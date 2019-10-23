from __future__ import unicode_literals

import os
import imp
import django
import markdown
from django_comments_tree.render import render_draftjs, render_plain

from .settings import *

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgres',
        'NAME':     'django_comments_tree',
        'USER':     'django_user',
        'PASSWORD': 'testing_password',
        'HOST':     'localhost',
        'PORT':     '5440',
    }
}

