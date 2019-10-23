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

from django_comments_tree.models import (LIKEDIT_FLAG, DISLIKEDIT_FLAG,
                                         TreeCommentFlag)
from django_comments_tree.tests.factories import (ArticleFactory,
                                                  UserFactory,
                                                  TreeCommentFactory,
                                                  TreeCommentFlagFactory)


class ManagerTestBase(DjangoTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.article_1 = ArticleFactory.create()
        cls.article_2 = ArticleFactory.create()
        cls.user1 = UserFactory.create()
        cls.user2 = UserFactory.create()
        cls.site = Site.objects.get(pk=1)
        cls.root_1 = TreeComment.objects.get_or_create_root(cls.article_1)
        cls.root_2 = TreeComment.objects.get_or_create_root(cls.article_2)

        cls.c1list = []
        cls.c2list = []
        for x in range(10):
            cls.c1list.append(cls.root_1.add_child(comment=f"Comment Root1 {x}"))
            cls.c2list.append(cls.root_2.add_child(comment=f"Comment Root2 {x}"))

        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[0],
                                      flag=LIKEDIT_FLAG)
        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[1],
                                      flag=DISLIKEDIT_FLAG)
        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[2],
                                      flag=LIKEDIT_FLAG)
        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[3],
                                      flag=DISLIKEDIT_FLAG)
        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[7],
                                      flag=LIKEDIT_FLAG)
        TreeCommentFlagFactory.create(user=cls.user1,
                                      comment=cls.c1list[7],
                                      flag=TreeCommentFlag.SUGGEST_REMOVAL)



class TestModelManager(ManagerTestBase):

    def test_user_likes(self):

        result = TreeComment.objects.user_flags_for_model(self.user1,
                                                          self.article_1)

        self.assertIsNotNone(result)

        self.assertIn('user', result)
        likes = result['liked']
        dislikes = result['disliked']
        reported = result['reported']
        self.assertEqual(len(likes), 3)
        self.assertEqual(len(dislikes), 2)
        self.assertEqual(len(reported), 1)
        self.assertEqual(likes, [self.c1list[0].id, self.c1list[2].id, self.c1list[7].id])
