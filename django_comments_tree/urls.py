from django.conf.urls import include, url

from rest_framework.urlpatterns import format_suffix_patterns

from django_comments_tree import api
from django_comments_tree.views.comments import (
    sent, confirm, mute, reply, FlagView, like, like_done,
    dislike, dislike_done
)

urlpatterns = [
    url(r'^sent/$', sent, name='comments-tree-sent'),
    url(r'^confirm/(?P<key>[^/]+)/$', confirm,
        name='comments-tree-confirm'),
    url(r'^mute/(?P<key>[^/]+)/$', mute, name='comments-tree-mute'),
    url(r'^reply/(?P<cid>[\d]+)/$', reply, name='comments-tree-reply'),

    # Remap comments-flag to check allow-flagging is enabled.
    url(r'^flag/(\d+)/$', FlagView.as_view(), name='comments-flag'),
    # New flags in addition to those provided by django-contrib-comments.
    url(r'^like/(\d+)/$', like, name='comments-tree-like'),
    url(r'^liked/$', like_done, name='comments-tree-like-done'),
    url(r'^dislike/(\d+)/$', dislike, name='comments-tree-dislike'),
    url(r'^disliked/$', dislike_done, name='comments-tree-dislike-done'),

    # API handlers.
    url(r'^api/comment/$', api.CommentCreate.as_view(),
        name='comments-tree-api-create'),
    url(r'^api/(?P<content_type>\w+[-]{1}\w+)/(?P<object_pk>[-\w]+)/$',
        api.CommentList.as_view(), name='comments-tree-api-list'),
    url(r'^api/(?P<content_type>\w+[-]{1}\w+)/(?P<object_pk>[-\w]+)/count/$',
        api.CommentCount.as_view(), name='comments-tree-api-count'),
    url(r'^api/feedback/$', api.ToggleFeedbackFlag.as_view(),
        name='comments-tree-api-feedback'),
    url(r'^api/flag/$', api.CreateReportFlag.as_view(),
        name='comments-tree-api-flag'),

    url(r'', include("django_comments.urls")),
]


urlpatterns = format_suffix_patterns(urlpatterns)
