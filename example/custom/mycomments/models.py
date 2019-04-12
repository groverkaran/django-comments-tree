from django.db import models

from django_comments_tree.models import TreeComment


class MyComment(TreeComment):
    title = models.CharField(max_length=256)
