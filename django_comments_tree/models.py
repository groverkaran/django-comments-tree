from typing import Optional, List

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import signing
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_comments_tree.signals import comment_was_flagged

from django_comments_tree.conf import settings
from treebeard.mp_tree import MP_Node, MP_NodeManager

from .abstract import CommentAbstractModel

LIKEDIT_FLAG = "I liked it"
DISLIKEDIT_FLAG = "I disliked it"


def max_thread_level_for_content_type(content_type):
    app_model = "%s.%s" % (content_type.app_label, content_type.model)
    if app_model in settings.COMMENTS_TREE_MAX_THREAD_LEVEL_BY_APP_MODEL:
        return settings.COMMENTS_TREE_MAX_THREAD_LEVEL_BY_APP_MODEL[app_model]
    else:
        return settings.COMMENTS_TREE_MAX_THREAD_LEVEL


class MaxThreadLevelExceededException(Exception):
    def __init__(self, comment):
        self.comment = comment
        # self.max_by_app = max_thread_level_for_content_type(content_type)

    def __str__(self):
        return "Max thread level reached for comment %d" % self.comment.id


class CommentManager(MP_NodeManager):

    def get_root(self, obj):
        """ Return the root for the given object """
        try:
            ct = ContentType.objects.get_for_model(obj)
            assoc = CommentAssociation.objects.get(content_type=ct, object_id=obj.id)
            return assoc.root
        except ObjectDoesNotExist:
            return None

    def get_or_create_root(self, obj, site=None):
        ct = ContentType.objects.get_for_model(obj)

        if site is None:
            site = Site.objects.get(pk=1)

        try:
            assoc = CommentAssociation.objects.get(content_type=ct,
                                                   object_id=obj.id,
                                                   site=site)
        except ObjectDoesNotExist:
            root = TreeComment.add_root()
            assoc = CommentAssociation.objects.create(content_type=ct,
                                                      object_id=obj.id,
                                                      content_object=obj,
                                                      site=site,
                                                      root=root)
        if assoc:
            return assoc.root
        return None

    def get_or_create_root_type_and_id(self, ct, object_id):
        return None

    def create_for_object(self, obj, comment=''):
        root = self.get_or_create_root(obj)
        return root.add_child(comment=comment)

    def in_moderation(self):
        """
        QuerySet for all comments currently in the moderation queue.
        """
        return self.get_queryset().filter(is_public=False, is_removed=False)

    def for_model(self, model):
        """
        QuerySet for all comments for a particular model (either an instance or
        a class).

        Updated: this can't return a queryset, since MP_Node are queriable that way

        """
        ct = ContentType.objects.get_for_model(model)

        qs = self.get_queryset().filter(content_type=ct)
        if isinstance(model, models.Model):
            qs = qs.filter(object_id=model._get_pk_val())
        return qs

    def for_app_models(self, *args, **kwargs) -> Optional[models.QuerySet]:
        """Return TreeComments for pairs "app.model" given in args"""
        content_types = []
        for app_model in args:
            app, model = app_model.split(".")
            content_types.append(ContentType.objects.get(app_label=app,
                                                         model=model))
        return self.for_content_types(content_types, **kwargs)

    def for_content_types(self,
                          content_types: List[str],
                          site: int = None) -> Optional[models.QuerySet]:
        """
        Return all descendants of the content type.
        :param content_types:
        :param site:
        :return:
        """
        filter_fields = {'content_type__in': content_types}
        if site is not None:
            filter_fields['site'] = site
        associations = CommentAssociation.objects.filter(**filter_fields)
        parent_paths = []

        for assoc in associations:
            parent_paths.append(assoc.root.path)

        Qlist = [Q(path__startswith=path) for path in parent_paths]
        myQ = Qlist.pop()
        for Qitem in Qlist:
            myQ |= Qitem

        qs = TreeComment.objects.filter(depth__gte=2).filter(myQ)
        return qs

    def count_for_content_types(self, content_types: List[str], site: int = None) -> int:
        count = 0
        filter_fields = {'content_type__in': content_types}
        if site is not None:
            filter_fields['site'] = site
        associations = CommentAssociation.objects.filter(**filter_fields)
        for assoc in associations:
            count += assoc.root.get_descendants().count()
        return count

    def get_queryset(self):
        qs = super().get_queryset()
        return qs


class CommentAssociation(models.Model):
    """
    Associate a tree node with a particular model by GenericForeignKey

    ToDo: Review the proper way to use GFK's. Do I need all of the other parts?
    """

    # Root of comments for the associated model
    root = models.ForeignKey('TreeComment', on_delete=models.CASCADE, null=True)

    # Content-object field
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s",
                                     on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_id")

    # Retained a legacy. Remove once I determine it is not needed
    # object_pk = models.TextField(_('object ID'))

    # Metadata about the comment
    # ToDo: Why do I need this?
    site = models.ForeignKey(Site, on_delete=models.CASCADE)

    @property
    def object_pk(self):
        return str(self.object_id)


class TreeComment(MP_Node, CommentAbstractModel):
    node_order_by = ['submit_date']

    def __init__(self, *args, **kwargs):
        self._association = None
        super().__init__(*args, **kwargs)

    followup = models.BooleanField(blank=True, default=False,
                                   help_text=_("Notify follow-up comments"))
    objects = CommentManager()

    def add_child(self, *args, comment=None, **kwargs):
        """ Check for maximum depth before adding child """
        depth = self.depth
        if depth > settings.COMMENTS_TREE_MAX_THREAD_LEVEL:
            raise MaxThreadLevelExceededException(comment)

        if 'instance' in kwargs:
            child = super().add_child(*args, **kwargs)
        else:
            child = super().add_child(*args, comment=comment, **kwargs)
        return child

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            if not self.is_root():
                root = self.get_root()
                try:
                    assoc = CommentAssociation.objects.get(root=root)
                    max_level = max_thread_level_for_content_type(assoc.content_type)
                    if max_level and self.get_depth() > max_level:
                        raise MaxThreadLevelExceededException(self)
                except Exception:
                    pass
            kwargs["force_insert"] = False
            super().save(*args, **kwargs)

    def get_reply_url(self):
        return reverse("comments-tree-reply", kwargs={"cid": self.pk})

    def allow_thread(self):
        if self.get_depth() < max_thread_level_for_content_type(self.content_type):
            return True
        else:
            return False

    @property
    def association(self):
        """
        Return the content type for this comment. We have to search from the root for this.
        Cache the value though.
        """
        if self._association is None:
            root = self if self.is_root() else self.get_root()
            self._association = CommentAssociation.objects.get(root=root)

        return self._association

    @property
    def content_type(self):
        """
        Return the content type for this comment. We have to search from the root for this.
        Cache the value though.
        """
        assoc = self.association
        if assoc:
            return assoc.content_type

        return None

    @property
    def object_id(self):
        """ Accessor added for compatibility with django_contrib.comments """
        assoc = self.association
        if assoc:
            return assoc.object_id

        return None

    @property
    def site(self):
        """ Accessor added for compatibility with django_contrib.comments """
        assoc = self.association
        if assoc:
            return assoc.site

        return None

    @classmethod
    def tree_from_comment(cls, root,
                          filter_public=True,):
        """
        Return a recursive structure with comments and their children,
        starting at the given root.
        """
        retval = []
        children = root.get_children().order_by('submit_date')
        if filter_public:
            children = children.filter(is_public=True)
        for child in children:
            data = {
                "comment": child,
                "children": cls.tree_from_comment(
                    child,
                    filter_public=filter_public
                )
            }
            retval.append(data)
        return retval

    @classmethod
    def tree_for_associated_object(cls, obj,
                                   with_flagging=False,
                                   with_feedback=False,
                                   user=None):

        root = TreeComment.objects.get_or_create_root(obj)
        data = cls.tree_from_comment(root)
        return data

    def users_flagging(self, flag):
        return [obj.user for obj in self.flags.filter(flag=flag)]


@receiver(comment_was_flagged)
def unpublish_nested_comments_on_removal_flag(sender, comment, flag, **kwargs):
    if flag.flag == TreeCommentFlag.MODERATOR_DELETION:
        TreeComment.objects.filter(~(Q(pk=comment.id)), parent_id=comment.id) \
            .update(is_public=False)


class DummyDefaultManager:
    """
    Dummy Manager to mock django's CommentForm.check_for_duplicate method.
    """

    def __getattr__(self, name):
        return lambda *args, **kwargs: []

    def using(self, *args, **kwargs):
        return self


class TmpTreeComment(dict):
    """
    Temporary TreeComment to be pickled, zipped and appended to a URL.
    """
    _default_manager = DummyDefaultManager()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            if self.get('tree_comment'):
                try:
                    return getattr(self.get('tree_comment'), key)
                except KeyError:
                    pass
                except Exception:
                    pass
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def save(self, *args, **kwargs):
        pass

    def _get_pk_val(self):
        if self.tree_comment:
            return self.tree_comment._get_pk_val()
        else:
            content_type = "%s.%s" % self.content_type.natural_key()
            return signing.dumps("%s:%s" % (content_type, self.object_id))

    def __setstate__(self, state):
        ct_key = state.pop('content_type_key')
        ctype = ContentType.objects.get_by_natural_key(*ct_key)
        self.update(
            state,
            content_type=ctype,
            content_object=ctype.get_object_for_this_type(
                pk=state['object_id']
            )
        )

    def __reduce__(self):
        state = {k: v for k, v in self.items() if k != 'content_object'}
        ct = state.pop('content_type')
        state['content_type_key'] = ct.natural_key()
        return (TmpTreeComment, (), state,)


# ----------------------------------------------------------------------
class BlackListedDomain(models.Model):
    """
    A blacklisted domain from which comments should be discarded.
    Automatically populated with a small amount of spamming domains,
    gathered from http://www.joewein.net/spam/blacklist.htm

    You can download for free a recent version of the list, and subscribe
    to get notified on changes. Changes can be fetched with rsync for a
    small fee (check their conditions, or use any other Spam filter).
    """
    domain = models.CharField(max_length=200, db_index=True)

    def __str__(self):
        return self.domain

    class Meta:
        ordering = ('domain',)


class TreeCommentFlag(models.Model):
    """
    Records a flag on a comment. This is intentionally flexible; right now, a
    flag could be:

        * A "removal suggestion" -- where a user suggests a comment for (potential) removal.

        * A "moderator deletion" -- used when a moderator deletes a comment.

    You can (ab)use this model to add other flags, if needed. However, by
    design users are only allowed to flag a comment with a given flag once;
    if you want rating look elsewhere.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name="treecomment_flags",
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        # Translators: 'comment' is a noun here.
        TreeComment, verbose_name=_('comment'), related_name="flags", on_delete=models.CASCADE,
    )
    # Translators: 'flag' is a noun here.
    flag = models.CharField(_('flag'), max_length=30, db_index=True)
    flag_date = models.DateTimeField(_('date'), default=None)

    # Constants for flag types
    SUGGEST_REMOVAL = "removal suggestion"
    MODERATOR_DELETION = "moderator deletion"
    MODERATOR_APPROVAL = "moderator approval"

    class Meta:
        unique_together = [('user', 'comment', 'flag')]
        verbose_name = _('comment flag')
        verbose_name_plural = _('comment flags')

    def __str__(self):
        return "%s flag of comment ID %s by %s" % (
            self.flag, self.comment_id, self.user.get_username()
        )

    def save(self, *args, **kwargs):
        if self.flag_date is None:
            self.flag_date = timezone.now()
        super().save(*args, **kwargs)
