from datetime import datetime
from textwrap import dedent
from os.path import join, dirname

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.conf import settings
from django.test import TestCase as DjangoTestCase

from django_comments_tree.models import (TreeComment, CommentAssociation,
                                         MaxThreadLevelExceededException)
from django_comments_tree.tests.models import Article, Diary


class ArticleBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.article_1 = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_2 = Article.objects.create(
            title="October", slug="october", body="What I did on October...")


class StructuredDataBase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site1 = Site.objects.get(pk=1)
        self.site2 = Site.objects.create(domain='site2.com', name='site2.com')

        self.root_1 = TreeComment.objects.get_or_create_root(self.article_1)
        self.root_1_pk = self.root_1.pk

        with open(join(dirname(__file__), 'data/draftjs_raw.json'), 'r') as fp:
            self.draft_raw = fp.read()

    def add_comments(self):
        """ Add top level comments """
        r = self.root_1
        r.add_child(comment="just a testing comment")
        r.add_child(comment="yet another comment")
        r.add_child(comment="and another one")
        r.add_child(comment="just a testing comment in site2")

    def add_replies(self):
        """ Add comment replies """
        children = self.root_1.get_children()
        for child in children:
            for x in range(3):
                child.add_child(comment=f"Reply {x} to {child.id}")


class TestWithNoChildren(StructuredDataBase):

    def test_has_no_results(self):
        root = self.root_1
        qs = root.get_descendants().order_by('submit_date')

        self.assertEqual(qs.count(), 0)

        data = TreeComment.structured_tree_data_for_queryset(qs)

        self.assertIsNotNone(data)
        self.assertEqual(['comments'], list(data.keys()))


class TestWithChildren(StructuredDataBase):

    def setUp(self):
        super().setUp()
        self.add_comments()

    def test_structured_result_with_children(self):

        root = self.root_1
        qs = root.get_descendants().order_by('submit_date')

        self.assertEqual(qs.count(), 4)

        data = TreeComment.structured_tree_data_for_queryset(qs)

        self.assertIsNotNone(data)


class TestWithGrandchildren(StructuredDataBase):

    def setUp(self):
        super().setUp()
        self.add_comments()
        self.add_replies()

    def test_structured_result_with_children(self):

        root = self.root_1
        qs = root.get_descendants().order_by('submit_date')

        self.assertEqual(qs.count(), 16)

        data = TreeComment.structured_tree_data_for_queryset(qs)

        self.assertIsNotNone(data)
