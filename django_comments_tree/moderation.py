"""
A generic comment-moderation system which allows configuration of
moderation options on a per-model basis.

To use, do two things:

1. Create or import a subclass of ``CommentModerator`` defining the
   options you want.

2. Import ``moderator`` from this module and register one or more
   models, passing the models and the ``CommentModerator`` options
   class you want to use.


Example
-------

First, we define a simple model class which might represent entries in
a Weblog::

    from django.db import models

    class Entry(models.Model):
        title = models.CharField(max_length=250)
        body = models.TextField()
        pub_date = models.DateField()
        enable_comments = models.BooleanField()

Then we create a ``CommentModerator`` subclass specifying some
moderation options::

    from django_comments_tree.moderation import CommentModerator, moderator

    class EntryModerator(CommentModerator):
        email_notification = True
        enable_field = 'enable_comments'

And finally register it for moderation::

    moderator.register(Entry, EntryModerator)

This sample class would apply two moderation steps to each new
comment submitted on an Entry:

* If the entry's ``enable_comments`` field is set to ``False``, the
  comment will be rejected (immediately deleted).

* If the comment is successfully posted, an email notification of the
  comment will be sent to site staff.

For a full list of built-in moderation options and other
configurability, see the documentation for the ``CommentModerator``
class.

"""

import datetime

from django import VERSION
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.translation import ugettext as _

try:
    from django.contrib.sites.shortcuts import get_current_site
except ImportError:
    from django.contrib.sites.models import get_current_site

from django.template import Context, loader

from django_comments_tree import get_model
from django_comments_tree.signals import (comment_will_be_posted,
                                          comment_was_posted,
                                          comment_was_flagged)
from django_comments_tree.models import TreeCommentFlag

from django_comments_tree.conf import settings
from django_comments_tree.models import BlackListedDomain, TmpTreeComment
from django_comments_tree.signals import confirmation_received
from django_comments_tree.utils import send_mail


class AlreadyModerated(Exception):
    """
    Raised when a model which is already registered for moderation is
    attempting to be registered again.

    """
    pass


class NotModerated(Exception):
    """
    Raised when a model which is not registered for moderation is
    attempting to be unregistered.

    """
    pass


class CommentModerator(object):
    """
    Encapsulates comment-moderation options for a given model.

    This class is not designed to be used directly, since it doesn't
    enable any of the available moderation options. Instead, subclass
    it and override attributes to enable different options::

    ``auto_close_field``
        If this is set to the name of a ``DateField`` or
        ``DateTimeField`` on the model for which comments are
        being moderated, new comments for objects of that model
        will be disallowed (immediately deleted) when a certain
        number of days have passed after the date specified in
        that field. Must be used in conjunction with
        ``close_after``, which specifies the number of days past
        which comments should be disallowed. Default value is
        ``None``.

    ``auto_moderate_field``
        Like ``auto_close_field``, but instead of outright
        deleting new comments when the requisite number of days
        have elapsed, it will simply set the ``is_public`` field
        of new comments to ``False`` before saving them. Must be
        used in conjunction with ``moderate_after``, which
        specifies the number of days past which comments should be
        moderated. Default value is ``None``.

    ``close_after``
        If ``auto_close_field`` is used, this must specify the
        number of days past the value of the field specified by
        ``auto_close_field`` after which new comments for an
        object should be disallowed. Default value is ``None``.

    ``email_notification``
        If ``True``, any new comment on an object of this model
        which survives moderation will generate an email to site
        staff. Default value is ``False``.

    ``enable_field``
        If this is set to the name of a ``BooleanField`` on the
        model for which comments are being moderated, new comments
        on objects of that model will be disallowed (immediately
        deleted) whenever the value of that field is ``False`` on
        the object the comment would be attached to. Default value
        is ``None``.

    ``moderate_after``
        If ``auto_moderate_field`` is used, this must specify the number
        of days past the value of the field specified by
        ``auto_moderate_field`` after which new comments for an
        object should be marked non-public. Default value is
        ``None``.

    Most common moderation needs can be covered by changing these
    attributes, but further customization can be obtained by
    subclassing and overriding the following methods. Each method will
    be called with three arguments: ``comment``, which is the comment
    being submitted, ``content_object``, which is the object the
    comment will be attached to, and ``request``, which is the
    ``HttpRequest`` in which the comment is being submitted::

    ``allow``
        Should return ``True`` if the comment should be allowed to
        post on the content object, and ``False`` otherwise (in
        which case the comment will be immediately deleted).

    ``email``
        If email notification of the new comment should be sent to
        site staff or moderators, this method is responsible for
        sending the email.

    ``moderate``
        Should return ``True`` if the comment should be moderated
        (in which case its ``is_public`` field will be set to
        ``False`` before saving), and ``False`` otherwise (in
        which case the ``is_public`` field will not be changed).

    Subclasses which want to introspect the model for which comments
    are being moderated can do so through the attribute ``_model``,
    which will be the model class.

    """
    auto_close_field = None
    auto_moderate_field = None
    close_after = None
    email_notification = False
    enable_field = None
    moderate_after = None

    def __init__(self, model):
        self._model = model

    def _get_delta(self, now, then):
        """
        Internal helper which will return a ``datetime.timedelta``
        representing the time between ``now`` and ``then``. Assumes
        ``now`` is a ``datetime.date`` or ``datetime.datetime`` later
        than ``then``.

        If ``now`` and ``then`` are not of the same type due to one of
        them being a ``datetime.date`` and the other being a
        ``datetime.datetime``, both will be coerced to
        ``datetime.date`` before calculating the delta.

        """
        if now.__class__ is not then.__class__:
            now = datetime.date(now.year, now.month, now.day)
            then = datetime.date(then.year, then.month, then.day)
        if now < then:
            raise ValueError(f"Cannot determine moderation rules "
                             f" because date field is set to a value"
                             f" in the future")
        return now - then

    def allow(self, comment, content_object, request):
        """
        Determine whether a given comment is allowed to be posted on
        a given object.

        Return ``True`` if the comment should be allowed, ``False
        otherwise.

        """
        if self.enable_field:
            if not getattr(content_object, self.enable_field):
                return False
        if self.auto_close_field and self.close_after is not None:
            close_after_date = getattr(content_object, self.auto_close_field)
            if close_after_date is not None and self._get_delta(timezone.now(),
                                                                close_after_date
                                                                ).days >= self.close_after:
                return False
        return True

    def moderate(self, comment, content_object, request):
        """
        Determine whether a given comment on a given object should be
        allowed to show up immediately, or should be marked non-public
        and await approval.

        Return ``True`` if the comment should be moderated (marked
        non-public), ``False`` otherwise.

        """
        if self.auto_moderate_field and self.moderate_after is not None:
            moderate_after_date = getattr(content_object, self.auto_moderate_field)
            if moderate_after_date is not None and self._get_delta(
                    timezone.now(), moderate_after_date).days >= self.moderate_after:
                return True
        return False

    def email(self, comment, content_object, request):
        """
        Send email notification of a new comment to site staff when email
        notifications have been requested.

        """
        if not self.email_notification:
            return
        recipient_list = [manager_tuple[1] for manager_tuple in settings.MANAGERS]
        t = loader.get_template('comments/comment_notification_email.txt')
        c = {
            'comment': comment,
            'content_object': content_object,
        }
        subject = _('[%(site)s] New comment posted on "%(object)s"') % {
            'site': get_current_site(request).name,
            'object': content_object,
        }
        message = t.render(c)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=True)


class Moderator(object):
    """
    Handles moderation of a set of models.

    An instance of this class will maintain a list of one or more
    models registered for comment moderation, and their associated
    moderation classes, and apply moderation to all incoming comments.

    To register a model, obtain an instance of ``Moderator`` (this
    module exports one as ``moderator``), and call its ``register``
    method, passing the model class and a moderation class (which
    should be a subclass of ``CommentModerator``). Note that both of
    these should be the actual classes, not instances of the classes.

    To cease moderation for a model, call the ``unregister`` method,
    passing the model class.

    For convenience, both ``register`` and ``unregister`` can also
    accept a list of model classes in place of a single model; this
    allows easier registration of multiple models with the same
    ``CommentModerator`` class.

    The actual moderation is applied in two phases: one prior to
    saving a new comment, and the other immediately after saving. The
    pre-save moderation may mark a comment as non-public or mark it to
    be removed; the post-save moderation may delete a comment which
    was disallowed (there is currently no way to prevent the comment
    being saved once before removal) and, if the comment is still
    around, will send any notification emails the comment generated.

    """

    def __init__(self):
        self._registry = {}
        self.connect()

    def connect(self):
        """
        Hook up the moderation methods to pre- and post-save signals
        from the comment models.

        """
        comment_will_be_posted.connect(self.pre_save_moderation, sender=get_model())
        comment_was_posted.connect(self.post_save_moderation, sender=get_model())

    def register(self, model_or_iterable, moderation_class):
        """
        Register a model or a list of models for comment moderation,
        using a particular moderation class.

        Raise ``AlreadyModerated`` if any of the models are already
        registered.

        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyModerated(f"The model '{model._meta.model_name}' "
                                       f" is already being moderated")
            self._registry[model] = moderation_class(model)

    def unregister(self, model_or_iterable):
        """
        Remove a model or a list of models from the list of models
        whose comments will be moderated.

        Raise ``NotModerated`` if any of the models are not currently
        registered for moderation.

        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotModerated(
                    f"The model '{model._meta.model_name}'"
                    f" is not currently being moderated")
            del self._registry[model]

    def pre_save_moderation(self, sender, comment, request, **kwargs):
        """
        Apply any necessary pre-save moderation steps to new
        comments.

        """
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        content_object = comment.content_object
        moderation_class = self._registry[model]

        # Comment will be disallowed outright (HTTP 403 response)
        if not moderation_class.allow(comment, content_object, request):
            return False

        if moderation_class.moderate(comment, content_object, request):
            comment.is_public = False

    def post_save_moderation(self, sender, comment, request, **kwargs):
        """
        Apply any necessary post-save moderation steps to new
        comments.

        """
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        self._registry[model].email(comment, comment.content_object, request)


class TreeCommentModerator(CommentModerator):
    """
    Encapsulates comment-moderation options for a given-model.

    This class extends ``django_comments.moderation.CommentModerator``. It's not
    designed to be used directly, since it doesn't enable any of the available
    moderation options. Instead, subclass it and override attributes to enable
    different options::

    ``removal_suggestion_notification``
        If ``True``, any new removal suggestion flag on an object
        of this model will generate an email to site staff. Default
        value is ``False``.

    Check parent class to see inherited options.

    Most common moderation needs can be covered by changing option attributes,
    but further customization can be obtained by subclassing and overriding
    the following method::

    ``notify_removal_suggestion``
         If removal suggestion notifications should be sent to site staff
         or moderators, this method is responsible for sending the email.

    Check the parent class to read about methods ``allow``, ``email``, and
    ``moderate``.

    """
    removal_suggestion_notification = None

    def notify_removal_suggestion(self, comment, content_object, request):
        if not self.removal_suggestion_notification:
            return
        recipient_list = [manager_tuple[1]
                          for manager_tuple in settings.MANAGERS]
        t = loader.get_template('django_comments_tree/'
                                'removal_notification_email.txt')
        c = {'comment': comment,
             'content_object': content_object,
             'current_site': get_current_site(request),
             'request': request}
        subject = ('[%s] Comment removal suggestion on "%s"' %
                   (c['current_site'].name, content_object))
        message = t.render(Context(c) if VERSION < (1, 8) else c)
        send_mail(subject, message, settings.COMMENTS_TREE_FROM_EMAIL,
                  recipient_list, fail_silently=True)


class SpamModerator(TreeCommentModerator):
    """
    Discard messages comming from blacklisted domains.

    The current list of blacklisted domains had been fetched from
    http://www.joewein.net/spam/blacklist.htm

    You can download for free a recent version of the list, and subscribe
    to get notified on changes. Changes can be fetched with rsync for a
    small fee (check their conditions, or use any other Spam filter).

    django-comments-tree approach against spam consist of requiring comment
    confirmation by email. However spam comments could be discarded even
    before sending the confirmation email by searching sender's domain in
    the list of blacklisted domains.

    ``SpamModerator`` uses the additional ``django_comments_tree`` model:
     * ``BlackListedDomain``

    Remember to update the content regularly through an external Spam
    filtering service.
    """

    def allow(self, comment, content_object, request):
        try:
            domain = comment.user_email.split('@', 1)[1]
        except IndexError:
            return False
        else:
            if (BlackListedDomain.objects.filter(domain=domain).count()):
                return False
            return super().allow(comment, content_object,
                                 request)


class TreeModerator(Moderator):
    def connect(self):
        comment_will_be_posted.connect(self.pre_save_moderation,
                                       sender=TmpTreeComment)
        confirmation_received.connect(self.post_save_moderation,
                                      sender=TmpTreeComment)
        comment_was_flagged.connect(self.comment_flagged,
                                    sender=get_model())

    def comment_flagged(self, sender, comment, flag, created, request,
                        **kwargs):
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        if flag.flag != TreeCommentFlag.SUGGEST_REMOVAL:
            return
        self._registry[model].notify_removal_suggestion(comment,
                                                        comment.association.content_object,
                                                        request)


moderator = TreeModerator()
