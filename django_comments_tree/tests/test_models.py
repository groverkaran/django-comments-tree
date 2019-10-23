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


class TreeCommentManagerTestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site1 = Site.objects.get(pk=1)
        self.site2 = Site.objects.create(domain='site2.com', name='site2.com')

        self.root_1 = TreeComment.objects.get_or_create_root(self.article_1)
        self.root_1_pk = self.root_1.pk
        self.root_2 = TreeComment.objects.get_or_create_root(self.article_1, site=self.site2)
        self.root_2_pk = self.root_2.pk

        with open(join(dirname(__file__), 'data/draftjs_raw.json'), 'r') as fp:
            self.draft_raw = fp.read()

    def post_comment_1(self):
        r = TreeComment.objects.get(pk=self.root_1_pk)
        r.add_child(comment="just a testing comment")

    def post_comment_2(self):
        r = TreeComment.objects.get(pk=self.root_2_pk)
        r.add_child(comment="yet another comment")

    def post_comment_3(self):
        r = TreeComment.objects.get(pk=self.root_1_pk)
        r.add_child(comment="and another one")

    def post_comment_4(self):
        r = TreeComment.objects.get(pk=self.root_2_pk)
        r.add_child(comment="just a testing comment in site2")

    def test_for_app_models(self):
        # there is no comment posted yet to article_1 nor article_2
        count = TreeComment.objects.for_app_models("tests.article").count()
        self.assertEqual(count, 0)
        self.post_comment_1()
        count = TreeComment.objects.for_app_models("tests.article").count()
        self.assertEqual(count, 1)
        self.post_comment_2()
        count = TreeComment.objects.for_app_models("tests.article").count()
        self.assertEqual(count, 2)
        self.post_comment_3()
        count = TreeComment.objects.for_app_models("tests.article").count()
        self.assertEqual(count, 3)
        self.post_comment_4()
        count = TreeComment.objects.for_app_models("tests.article").count()
        self.assertEqual(count, 4)

    def test_multi_site_for_app_models(self):
        self.post_comment_1()  # To site1.
        self.post_comment_4()  # To site2.
        count_site1 = TreeComment.objects.for_app_models("tests.article",
                                                         site=self.site1).count()
        self.assertEqual(count_site1, 1)
        count_site2 = TreeComment.objects.for_app_models("tests.article",
                                                         site=self.site2).count()
        self.assertEqual(count_site2, 1)

    def test_get_root_on_invalid_obj(self):
        """ get_root should return None with invalid obj"""

        r = TreeComment.objects.get_root(self.article_2)
        self.assertIsNone(r, 'Expected no root to be found')

    def test_create_comment_for_obj(self):
        """ Test out the custom manager method """
        comment = 'Test Value'
        c = TreeComment.objects.create_for_object(
            self.article_2, comment=comment
        )
        self.assertEqual(c.comment.raw, comment,
                         "Expected to create new comment here")

    def test_create_markdown_comment(self):
        """ Validate a very basic markdown render """
        comment = dedent('''
        #Heading
        Body Text
        ''').strip()
        comment_rendered = dedent('''
        <h1>Heading</h1>
        <p>Body Text</p>
        ''').strip()

        c = TreeComment.objects.create_for_object(
            self.article_2, comment=comment,
            comment_markup_type='markdown'
        )
        self.assertEqual(c.comment.raw, comment,
                         "Expected raw comment to match original")
        self.assertEqual(c.comment.rendered, comment_rendered,
                         "Expected rendered to match markdown output")

    def test_create_draftail_comment(self):
        """ Validate a very basic draftjs render """
        comment_rendered = dedent('''
        <p>Text 1.</p><p>Test 2.</p>
        ''').strip()

        c = TreeComment.objects.create_for_object(
            self.article_2, comment=self.draft_raw,
            comment_markup_type='draftjs'
        )
        self.assertEqual(c.comment.raw, self.draft_raw,
                         "Expected raw comment to match original")
        self.assertEqual(c.comment.rendered, comment_rendered,
                         "Expected rendered to match markdown output")

    # ToDo: in_moderation, for_model, count_for_content_types
    # ToDo: CommentAssociation: object_pk


# In order to test methods 'save' and '_calculate_thread_data', simulate the
# following threads, in order of arrival:
#
# testcase cmt.id   parent level-0  level-1  level-2
#  step1     1        -      c1                        <-                 cmt1
#  step1     2        -      c2                        <-                 cmt2
#  step2     3        1      --       c3               <-         cmt1 to cmt1
#  step2     4        1      --       c4               <-         cmt2 to cmt1
#  step3     5        2      --       c5               <-         cmt1 to cmt2
#  step4     6        5      --       --        c6     <- cmt1 to cmt1 to cmt2
#  step4     7        4      --       --        c7     <- cmt1 to cmt2 to cmt1
#  step5     8        3      --       --        c8     <- cmt1 to cmt1 to cmt1
#  step5     9        -      c9                        <-                 cmt9


def thread_test_step_1(article):
    """
    Add Two Comments for the article

    root -
      comment 1
      comment 2
    """
    site = Site.objects.get(pk=1)

    #TreeComment.objects.create()
    # post Comment 1 with parent_id 0
    root = TreeComment.objects.get_or_create_root(article, site=site)

    root.add_child(comment="comment 1 to article",
                   submit_date=datetime.now())
    root.refresh_from_db()

    # post Comment 2 with parent_id 0
    root.add_child(comment="comment 2 to article",
                   submit_date=datetime.now())
    root.refresh_from_db()


def thread_test_step_2(article):
    """
    Add 2 replies to the first comment

    root -
      comment 1
        reply 1
        reply 2
      comment 2

    """
    site = Site.objects.get(pk=1)

    root = TreeComment.objects.get_or_create_root(article, site=site)

    children = root.get_children()
    c1 = children[0]

    # post Comment 3 to parent_id 1
    c1.add_child(comment="comment 1 to comment 1")

    # post Comment 4 to parent_id 1
    c1.add_child(comment="comment 2 to comment 1")


def thread_test_step_3(article):
    """

    root -
      comment 1
        reply 1
        reply 2
      comment 2
        reply 1

    """
    site = Site.objects.get(pk=1)

    root = TreeComment.objects.get_or_create_root(article, site=site)

    c2 = root.get_children()[1]

    c2.add_child(comment="comment 1 to comment 2")


def thread_test_step_4(article):
    """

    root -
      comment 1
        reply 1
        reply 2
            reply 2.1
      comment 2
        reply 1
            reply 1.1

    """
    site = Site.objects.get(pk=1)

    root = TreeComment.objects.get_or_create_root(article, site=site)

    c1, c2 = root.get_children()

    c1_children = c1.get_children()
    c2_children = c2.get_children()

    c2_children[0].add_child(comment="cmt 1 to cmt 1 to cmt 2")

    c1_children[1].add_child(comment="cmt 1 to cmt 2 to cmt 1")


def thread_test_step_5(article):
    """
    Adds comments out to level 4

    root -
      comment 1
        reply 1
        reply 2
            reply 2.1
                reply 2.1.1
      comment 2
        reply 1
            reply 1.1
                reply 1.1.1

    """
    site = Site.objects.get(pk=1)

    root = TreeComment.objects.get_or_create_root(article, site=site)

    c1, c2 = root.get_children()

    c1_children = c1.get_children()
    c2_children = c2.get_children()

    c1_grandchildren_list = [c.get_children() for c in c1_children]
    c2_grandchildren_list = [c.get_children() for c in c2_children]

    for i, gc in enumerate(c1_grandchildren_list):
        for g in gc:
            g.add_child(comment=f'cmt1 to cmt{i} to cmt1 to cmt1')

    for i, gc in enumerate(c2_grandchildren_list):
        for g in gc:
            g.add_child(comment=f'cmt1 to cmt{i} to cmt1 to cmt2')


class BaseThreadStep1TestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)

    def test_threaded_comments_step_1_level_0(self):
        # comment 1
        root = TreeComment.objects.get_root(self.article_1)
        self.assertEqual(root.get_descendant_count(), 2, "Expected to have 2 comments/replies")
        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments, no replies")


class ThreadStep2TestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)

    def test_threaded_comments_step_2_level_0(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        c1, c2 = root.get_children()

        # comment 1
        self.assertEqual(c1.get_children_count(), 2, "Expected comment 1 to have 2 replies")
        # comment 2
        self.assertEqual(c2.get_children_count(), 0, "Expected comment 2 to have no replies")


class ThreadStep3TestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)
        thread_test_step_3(self.article_1)

    def test_threaded_comments_step_3_level_0(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 5, "Expected to have 5 total comments and replices")

    def test_threaded_comments_step_3_level_1(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 5, "Expected to have 5 total comments and replies")

        c1, c2 = root.get_children()

        # comment 1
        self.assertEqual(c1.get_children_count(), 2, "Expected comment 1 to have 2 replies")
        # comment 2
        self.assertEqual(c2.get_children_count(), 1, "Expected comment 2 to have 1 reply")


class ThreadStep4TestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)
        thread_test_step_3(self.article_1)
        thread_test_step_4(self.article_1)

    def test_threaded_comments_step_4_level_0(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 7, "Expected to have 7 total comments and replies")

        c1, c2 = root.get_children()

    def test_threaded_comments_step_4_level_1(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 7, "Expected to have 5 total comments and replies")

        c1, c2 = root.get_children()
        self.assertEqual(c1.get_children_count(), 2, "Expected 2 replies to comment 1")
        self.assertEqual(c2.get_children_count(), 1, "Expected 1 reply to comment 2")

        c1_children = c1.get_children()
        c2_children = c2.get_children()
        self.assertEqual(c1_children[1].get_children_count(), 1, "Expected 1 replies to comment 1, reply 2")
        self.assertEqual(c2_children[0].get_children_count(), 1, "Expected 1 reply to comment 2, reply 1")

    def test_threaded_comments_step_4_level_2(self):
        root = TreeComment.objects.get_root(self.article_1)


class ThreadStep5TestCase(ArticleBaseTestCase):
    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_2(self.article_1)
        thread_test_step_3(self.article_1)
        thread_test_step_4(self.article_1)
        thread_test_step_5(self.article_1)

    def test_threaded_comments_step_5_level_0(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 9, "Expected to have 5 total comments and replices")

        c1, c2 = root.get_children()

    def test_threaded_comments_step_5_level_1(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 9, "Expected to have 5 total comments and replices")

        c1, c2 = root.get_children()

    def test_threaded_comments_step_5_level_2(self):
        root = TreeComment.objects.get_root(self.article_1)

        self.assertEqual(root.get_children_count(), 2, "Expected to have 2 comments")
        self.assertEqual(root.get_descendant_count(), 9, "Expected to have 5 total comments and replices")

        c1, c2 = root.get_children()

        self.assertEqual(c1.get_children()[1].get_children()[0].get_children_count(),
                         1, "Expected 1 grandchild")
        self.assertEqual(c2.get_children()[0].get_children()[0].get_children_count(),
                         1, "Expected 1 grandchild")

    def test_exceed_max_thread_level_raises_exception(self):
        root = TreeComment.objects.get_or_create_root(self.article_1)
        LIMIT = settings.COMMENTS_TREE_MAX_THREAD_LEVEL
        with self.assertRaises(MaxThreadLevelExceededException):
            comment = root.get_descendants().order_by('-depth').first()
            print(f"Max Depth is {comment.thread_level}")
            while comment.thread_level < LIMIT:
                comment = comment.add_child(comment="Extending the level by one")
            comment.add_child(comment='This one should cause error')


def add_comment_to_diary_entry(diary):
    root = TreeComment.objects.get_or_create_root(diary)
    root.add_child(comment='This is a diary comment')


class DiaryBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.day_in_diary = Diary.objects.create(body="About Today...")
        self.root = TreeComment.objects.get_or_create_root(self.day_in_diary)

    def test_max_thread_level_by_app_model(self):
        self.root = TreeComment.objects.get_or_create_root(self.day_in_diary)
        c = self.root
        for x in range(1, settings.COMMENTS_TREE_MAX_THREAD_LEVEL+1):
            c = c.add_child(comment=f"Comment level {x}")
        with self.assertRaises(MaxThreadLevelExceededException):
            c.add_child(comment="Comment should cause an exception now")


class TestCommentsForModel(ArticleBaseTestCase):

    def setUp(self):
        super().setUp()
        thread_test_step_1(self.article_1)
        thread_test_step_1(self.article_2)

    def test_get_comments_for_model_type(self):
        comments = TreeComment.objects.for_model(Article)

        self.assertEqual(len(comments), 4)

    def test_get_comments_for_model_object(self):
        comments = TreeComment.objects.for_model(Article())

        self.assertEqual(len(comments), 0)

    def test_get_comments_for_model_instance(self):
        comments = TreeComment.objects.for_model(self.article_1)

        self.assertEqual(len(comments), 2)


class TestCommentsManager(ArticleBaseTestCase):

    def setUp(self):
        super().setUp()
        self.root = TreeComment.objects.get_or_create_root(self.article_1)
        thread_test_step_1(self.article_1)
        thread_test_step_1(self.article_2)

    def test_validate_association_on_root(self):
        self.assertIsNotNone(self.root.assoc)
        self.root.assoc = None
        self.root.save()
        self.assertIsNone(self.root.assoc)

        self.root = TreeComment.objects.get_or_create_root(self.article_1)
        self.assertIsNotNone(self.root.assoc)

    def test_moderation(self):

        moderated = TreeComment.objects.in_moderation()
        self.assertEqual(len(moderated.all()), 0)
        c1 = TreeComment.objects.first()
        c1.is_public = False
        c1.save()

        moderated = TreeComment.objects.in_moderation()
        self.assertEqual(len(moderated.all()), 1)

    def test_count_for_model(self):
        count1 = TreeComment.objects.count_for_model(Article)
        count2 = TreeComment.objects.count_for_model(self.article_1)
        count3 = TreeComment.objects.count_for_model(self.article_2)

        self.assertEqual(4, count1)
        self.assertEqual(2, count2)
        self.assertEqual(2, count3)



