from __future__ import unicode_literals
from django.conf import settings
import markdown
from django_comments_tree.render import render_draftjs

COMMENT_MAX_LENGTH = 3000

# Extra key to salt the TreeCommentForm.
COMMENTS_TREE_SALT = b""

# Whether comment posts should be confirmed by email.
COMMENTS_TREE_CONFIRM_EMAIL = True

# From email address.
COMMENTS_TREE_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

# Contact email address.
COMMENTS_TREE_CONTACT_EMAIL = settings.DEFAULT_FROM_EMAIL

# Maximum Thread Level.
COMMENTS_TREE_MAX_THREAD_LEVEL = 0

# Maximum Thread Level per app.model basis.
COMMENTS_TREE_MAX_THREAD_LEVEL_BY_APP_MODEL = {}

# Default order to list comments in.
COMMENTS_TREE_LIST_ORDER = ('submit_date',)

# Form class to use.
COMMENTS_TREE_FORM_CLASS = "django_comments_tree.forms.TreeCommentForm"

# Model to use.
COMMENTS_TREE_MODEL = "django_comments_tree.models.TreeComment"

# Send HTML emails.
COMMENTS_TREE_SEND_HTML_EMAIL = True

# Whether to send emails in separate threads or use the regular method.
# Set it to False to use a third-party app like django-celery-email or
# your own celery app.
COMMENTS_TREE_THREADED_EMAILS = True

# Define what commenting features a pair app_label.model can have.
# TODO: Put django-comments-tree settings under a dictionary, and merge
#       COMMENTS_TREE_MAX_THREAD_LEVEL_BY_APP_MODEL with this one.
COMMENTS_TREE_APP_MODEL_OPTIONS = {
    'default': {
        'allow_flagging': False,
        'allow_feedback': False,
        'show_feedback': False,
    }
}


# Define a function to return the user representation. Used by
# the web API to represent user strings in response objects.
def username(u):
    return u.username


COMMENTS_TREE_API_USER_REPR = username

# Set to true to enable Firebase notifications
COMMENTS_TREE_ENABLE_FIREBASE = False

COMMENTS_TREE_FIREBASE_KEY = None

# Default types we can use for comments
MARKUP_FIELD_TYPES = (
    ('markdown', markdown.markdown),
    ('Draft.js', render_draftjs),
)
