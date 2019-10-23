from datetime import datetime
from textwrap import dedent
from os.path import join, dirname

from django.db import connection, reset_queries
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.conf import settings
from django.test import TestCase as DjangoTestCase, override_settings

from django_comments_tree.models import (TreeComment, CommentAssociation,
                                         MaxThreadLevelExceededException)
from django_comments_tree.tests.models import Article, Diary


class ArticleBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.article_1 = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_2 = Article.objects.create(
            title="October", slug="october", body="What I did on October...")

    def add_comment(self, root, comment="Just a comment"):
        """
        Add Two Comments for the article

        root -
          comment 1
          comment 2
        """
        child = root.add_child(comment=comment,
                       submit_date=datetime.now())
        #root.refresh_from_db()
        return child

    def add_comments(self, root, level=2):
        current = root
        for lvl in range(level):
            current = self.add_comment(current)


class CommentAssociationTestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site = Site.objects.get(pk=1)
        self.root = TreeComment.objects.get_or_create_root(self.article_1)

    @override_settings(DEBUG=True)
    def test_association_is_added(self):
        root = self.root
        reset_queries()
        comment = self.add_comment(root)

        self.assertEqual(comment.assoc, root.commentassociation)

        # Only the insert of comment and update of root depth
        self.assertEqual(len(connection.queries), 2)

    @override_settings(DEBUG=True)
    def test_association_is_added_at_depth(self):
        root = self.root
        reset_queries()
        comment = self.add_comment(root)
        comment2 = self.add_comment(comment)
        comment3 = self.add_comment(comment2)

        self.assertEqual(comment2.assoc, root.commentassociation)
        self.assertEqual(comment3.assoc, root.commentassociation)

        # Only the insert of comment and update of root depth
        self.assertEqual(len(connection.queries), 6)

    def test_association_is_updated_on_change(self):
        root = self.root
        comment = self.add_comment(root)
        comment2 = self.add_comment(comment)
        comment3 = self.add_comment(comment2)

        self.assertEqual(comment2.assoc, root.commentassociation)
        self.assertEqual(comment3.assoc, root.commentassociation)


