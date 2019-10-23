try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
import unittest

from django.contrib.auth.models import AnonymousUser
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase as DjangoTestCase

from django_comments_tree.tests.models import Article, Diary
from django_comments_tree.tests.test_models import (
    thread_test_step_1, thread_test_step_2, thread_test_step_3,
    thread_test_step_4, thread_test_step_5, add_comment_to_diary_entry)

from django_comments_tree.models import TreeComment

class GetCommentCountTestCase(DjangoTestCase):
    def setUp(self):
        self.article_1 = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_2 = Article.objects.create(
            title="October", slug="october", body="What I did on October...")
        self.day_in_diary = Diary.objects.create(body="About Today...")
        
    def test_get_comment_count_for_one_model(self):
        thread_test_step_1(self.article_1)
        t = ("{% load comments_tree %}"
             "{% get_treecomment_count as varname for tests.article %}"
             "{{ varname }}")
        self.assertEqual(Template(t).render(Context()), '2')

    def test_get_comment_count_for_two_models(self):
        thread_test_step_1(self.article_1)
        add_comment_to_diary_entry(self.day_in_diary)
        t = ("{% load comments_tree %}"
             "{% get_treecomment_count as varname"
             "   for tests.article tests.diary %}"
             "{{ varname }}")
        self.assertEqual(Template(t).render(Context()), '3')
        

class LastCommentsTestCase(DjangoTestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.day_in_diary = Diary.objects.create(body="About Today...")
        thread_test_step_1(self.article)
        thread_test_step_2(self.article)
        thread_test_step_3(self.article)
        add_comment_to_diary_entry(self.day_in_diary)
        
    def test_render_last_comments(self):
        t = ("{% load comments_tree %}"
             "{% render_last_treecomments 5 for tests.article tests.diary %}")
        output = Template(t).render(Context())
        self.assertEqual(output.count('<a name='), 5)
        self.assertEqual(output.count('<a name="c6">'), 1)
        self.assertEqual(output.count('<a name="c5">'), 1)
        self.assertEqual(output.count('<a name="c4">'), 1)
        self.assertEqual(output.count('<a name="c3">'), 1)
        self.assertEqual(output.count('<a name="c2">'), 1)
        # We added 6 comments, and we render the last 5, so
        # the first one must not be rendered in the output.
        self.assertEqual(output.count('<a name="c1">'), 0)

    def test_get_last_comments(self):
        t = ("{% load comments_tree %}"
             "{% get_last_treecomments 5 as last_comments"
             "   for tests.article tests.diary %}"
             "{% for comment in last_comments %}"
             "<comment>{{ comment.id }}</comment>"
             "{% endfor %}")
        output = Template(t).render(Context())
        self.assertEqual(output.count('<comment>'), 5)
        self.assertEqual(output.count('<comment>6</comment>'), 1)
        self.assertEqual(output.count('<comment>5</comment>'), 1)
        self.assertEqual(output.count('<comment>4</comment>'), 1)
        self.assertEqual(output.count('<comment>3</comment>'), 1)
        self.assertEqual(output.count('<comment>2</comment>'), 1)
        # We added 6 comments, and we render the last 5, so
        # the first one must not be rendered in the output.
        self.assertEqual(output.count('<comment>1</comment>'), 0)


class CommentsTestCase(DjangoTestCase):
    def setUp(self):
        self.article = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.day_in_diary = Diary.objects.create(body="About Today...")
        thread_test_step_1(self.article)
        thread_test_step_2(self.article)
        thread_test_step_3(self.article)
        thread_test_step_4(self.article)
        thread_test_step_5(self.article)

    def test_render_comment_tree(self):
        t = ("{% load comments_tree %}"
             "{% render_treecomment_tree for object %}")
        output = Template(t).render(Context({'object': self.article,
                                             'user': AnonymousUser()}))
        self.assertEqual(output.count('<a name='), 9)
        # See test_models.py, ThreadStep5TestCase to get a quick
        # view of the comments posted and their thread structure.
        id_list = [2, 4, 5, 8, 9, 3, 6, 7, 10]
        pos_list = [output.index(f'<a name="c{id}"></a>') for id in id_list]
        for pos in pos_list:
            self.assertTrue(pos > 0)

        for x in range(0, len(id_list)-1):
            p1 = pos_list[x]
            p2 = pos_list[x+1]
            self.assertTrue(p1 < p2)
