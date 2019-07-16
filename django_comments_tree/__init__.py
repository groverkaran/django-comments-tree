from django.utils.module_loading import import_string

from .feeds import LatestCommentFeed  # noqa
from .signals import comment_was_posted  # noqa


default_app_config = 'django_comments_tree.apps.Config'


def get_model():
    from django_comments_tree.conf import settings
    return import_string(settings.COMMENTS_TREE_MODEL)


def get_form():
    from django_comments_tree.conf import settings
    return import_string(settings.COMMENTS_TREE_FORM_CLASS)


VERSION = (0, 1, 0, 'b', 1)  # following PEP 440


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    if VERSION[3] != 'f':
        version = '%s%s%s' % (version, VERSION[3], VERSION[4])
    return version
