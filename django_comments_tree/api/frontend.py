from django.contrib.contenttypes.models import ContentType
from django_comments.forms import CommentSecurityForm
from django_comments_tree import get_model as get_comment_model
from django_comments_tree.conf import settings
from rest_framework.response import Response
from rest_framework.reverse import reverse

TreeComment = get_comment_model()


def commentbox_props(obj, user, request=None):
    """
    Returns a JSON object with the initial props for the CommentBox component.

    The returned JSON object contains the following attributes::
        {
            comment_count: <int>,  // Count of comments posted to the object.
            allow_comments: <bool>,  // Whether to allow comments to this post.
            current_user: <str as "user_id:user_name">,
            is_authenticated: <bool>,  // Whether current_user is authenticated.
            request_name: <bool>,  // True when auth user has no actual name.
            request_email_address: <bool>,  // True when auth user has no email.
            allow_flagging: false,
            allow_feedback: false,
            show_feedback: false,
            can_moderate: <bool>,  // Whether current_user can moderate.
            poll_interval: 2000, // Check for new comments every 2 seconds.
            feedback_url: <api-url-to-send-like/dislike-feedback>,
            delete_url: <api-url-for-moderators-to-remove-comment>,
            login_url: settings.LOGIN_URL,
            reply_url: <api-url-to-reply-comments>,
            flag_url: <api-url-to-suggest-comment-removal>,
            list_url: <api-url-to-list-comments>,
            count_url: <api-url-to-count-comments>,
            send_url: <api-irl-to-send-a-comment>,
            form: {
                content_type: <value>,
                object_pk: <value>,
                timestamp: <value>,
                security_hash: <value>
            },
            login_url: <only_when_user_is_not_authenticated>,
            like_url: <only_when_user_is_not_authenticated>,
            dislike_url: <only_when_user_is_not_authenticated>
        }
    """

    def _reverse(*args, **kwargs):
        """Inject the request, if provided, to generate absolute URLs"""
        return reverse(*args, request=request, **kwargs)

    form = CommentSecurityForm(obj)
    ctype = ContentType.objects.get_for_model(obj)
    queryset = TreeComment.objects.filter(content_type=ctype,
                                          object_pk=obj.pk,
                                          site__pk=settings.SITE_ID,
                                          is_public=True)
    ctype_slug = "%s-%s" % (ctype.app_label, ctype.model)
    d = {
        "comment_count": queryset.count(),
        "allow_comments": True,
        "current_user": "0:Anonymous",
        "request_name": False,
        "request_email_address": False,
        "is_authenticated": False,
        "allow_flagging": False,
        "allow_feedback": False,
        "show_feedback": False,
        "can_moderate": False,
        "poll_interval": 2000,
        "feedback_url": _reverse("comments-tree-api-feedback"),
        "delete_url": _reverse("comments-delete", args=(0,)),
        "reply_url": _reverse("comments-tree-reply", kwargs={'cid': 0}),
        "flag_url": _reverse("comments-flag", args=(0,)),
        "list_url": _reverse('comments-tree-api-list',
                             kwargs={'content_type': ctype_slug,
                                     'object_pk': obj.id}),
        "count_url": _reverse('comments-tree-api-count',
                              kwargs={'content_type': ctype_slug,
                                      'object_pk': obj.id}),
        "send_url": _reverse("comments-tree-api-create"),
        "form": {
            "content_type": form['content_type'].value(),
            "object_pk": form['object_pk'].value(),
            "timestamp": form['timestamp'].value(),
            "security_hash": form['security_hash'].value()
        }
    }
    try:
        user_is_authenticated = user.is_authenticated()
    except TypeError:  # Django >= 1.11
        user_is_authenticated = user.is_authenticated
    if user and user_is_authenticated:
        d['current_user'] = "%d:%s" % (
            user.pk, settings.COMMENTS_TREE_API_USER_REPR(user))
        d['is_authenticated'] = True
        d['can_moderate'] = user.has_perm("django_comments.can_moderate")
        d['request_name'] = True if not len(user.get_full_name()) else False
        d['request_email_address'] = True if not user.email else False
    else:
        d['login_url'] = "/admin/login/"
        d['like_url'] = reverse("comments-tree-like", args=(0,))
        d['dislike_url'] = reverse("comments-tree-dislike", args=(0,))

    return d


def commentbox_props_response(obj, user, request):
    """Return a Response containing React props for use with client-side JS.
    Can add as an extra action to a ViewSet as follows:

        @action(detail=True, methods=['get'],
                permission_classes=[permissions.IsAuthenticated])
        def comment_props(self, request, *args, **kwargs):
            return commentbox_props_response(self.get_object(),
                                             request.user, request)
    """
    return Response(data=commentbox_props(obj, user, request=request))
