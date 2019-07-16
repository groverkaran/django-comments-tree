from django.test import TestCase

import django_comments_tree
from django_comments_tree.models import TmpTreeComment
from django_comments_tree.forms import TreeCommentForm
from django_comments_tree.tests.models import Article


class GetFormTestCase(TestCase):

    def test_get_form(self):
        # check function django_comments_tree.get_form retrieves the due class
        self.assertTrue(django_comments_tree.get_form() == TreeCommentForm)


class TreeCommentFormTestCase(TestCase):

    def setUp(self):
        self.article = Article.objects.create(title="September",
                                              slug="september",
                                              body="What I did on September...")
        self.form = django_comments_tree.get_form()(self.article)

    def test_get_comment_model(self):
        # check get_comment_model retrieves the due model class
        self.assertTrue(self.form.get_comment_model() == TmpTreeComment)

    def test_get_comment_create_data(self):
        # as it's used in django_comments.views.comments
        data = {"name": "Daniel",
                "email": "danirus@eml.cc",
                "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal iene kleine..."}
        data.update(self.form.initial)
        form = django_comments_tree.get_form()(self.article, data)
        self.assertTrue(self.form.security_errors() == {})
        self.assertTrue(self.form.errors == {})
        comment = form.get_comment_object()

        # it does have the new field 'followup'
        self.assertTrue("followup" in comment)
