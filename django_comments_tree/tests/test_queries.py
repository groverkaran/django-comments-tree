import math
from typing import List
from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import TestCase as DjangoTestCase, override_settings
from django.utils import timezone

from django_comments_tree.models import (TreeComment)
from django_comments_tree.tests.models import Article

utime = lambda d: timezone.now() - timezone.timedelta(days=d)


class ArticleBaseTestCase(DjangoTestCase):
    def setUp(self):
        self.article_1 = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_2 = Article.objects.create(
            title="October", slug="october", body="What I did on October...")


def calc_count(n, x):
    return pow(math.ceil(pow(n, 1 / x)), x)


def parent_for(node, path_to_node):
    basepath = node._get_basepath(node.path, node.depth - 1)
    if basepath in path_to_node:
        return path_to_node.get(basepath).id
    return None


def make_lots_of_comments(root: TreeComment,
                          count: int = None,
                          depth: int = 5,
                          prefix: str = "C"):
    """ Make comments algorithmically and optionally randomly
        This can be called recursively, so that we can create
        a hierarchy of comments, for deep testing, and performance
        testing.

        root: node to attach comments to.
        count: int
    """
    count = count if count is not None else 2 ** depth
    total_comments = 0
    children = []
    for x in range(count):
        comment = f"{prefix}{x}"
        child = root.add_child(comment=comment)
        #print(f"Created comment {comment}")
        total_comments += 1
        children.append(child)
        if depth > 1:
            n = make_lots_of_comments(child,
                                      count=count // 2,
                                      depth=depth - 1,
                                      prefix=comment + "-R")
            total_comments += n
    return total_comments


def make_comments(root, spec, default_kwargs=None):
    """ Make nested comments, based on provided spec
    spec format:
        [('Comment',), ('Comment2', [('Child',)],)]
    A comment tuple has 3 possible arguments:
        comment: string
        children: array of comments
        kwargs: dict of arguments to comment creation

    """

    args_default = default_kwargs if default_kwargs is not None else {}
    for args in [list(x) for x in spec]:
        comment = args.pop(0) if len(args) else "Default Comment"
        child_spec = args.pop(0) if len(args) else []
        kwargs = args.pop(0) if len(args) else args_default

        child = root.add_child(comment=comment, **kwargs)
        make_comments(child, child_spec)


class TestTreeCommentQueries(ArticleBaseTestCase):

    def setUp(self):
        super().setUp()
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site1 = Site.objects.get(pk=1)
        self.site2 = Site.objects.create(domain='site2.com', name='site2.com')

        self.root_1 = TreeComment.objects.get_or_create_root(self.article_1)
        self.root_1_pk = self.root_1.pk
        self.root_2 = TreeComment.objects.get_or_create_root(
            self.article_1, site=self.site2)
        self.root_2_pk = self.root_2.pk

        r1 = TreeComment.objects.get(pk=self.root_1_pk)
        old = utime(10)
        new = utime(1)

        make_comments(r1, [
            ('Comment 1', [
                ('Comment 1, Reply 1',),
                ('Comment 1, Reply 2', [
                    ('Comment 1, Reply 2, Reply 1', [], {'updated_on': utime(1)})
                ], {'updated_on': utime(1.5)})
            ],),
            ('Comment 2', [
                ('Comment 2, Reply 1', [], {'updated_on': utime(1.5)},),
                ('Comment 2, Reply 2', [
                    ('Comment 2, Reply 2, Reply 1', [], {'updated_on': utime(0.5)},)
                ], {'updated_on': utime(1.3)},)
            ], {'updated_on': utime(1.6)}),
        ], {'updated_on': utime(5)})

        make_comments(self.root_2, [
            ('Comment 1', [
                ('Comment 1, Reply 1', [], {'is_public': False},),
                ('Comment 1, Reply 2', [
                    ('Comment 1, Reply 2, Reply 1', [], {'is_public': False},)
                ], {'is_public': False},)
            ],),
            ('Comment 2', [
                ('Comment 2, Reply 1',),
                ('Comment 2, Reply 2', [
                    ('Comment 2, Reply 2, Reply 1',)
                ],)
            ],),
        ], {'updated_on': utime(3)})

    def test_unfiltered_tree(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_1.refresh_from_db()
        print(self.root_1.get_descendant_count())
        print(self.root_1.get_children_count())
        tree = TreeComment.tree_from_comment(self.root_1)
        self.assertEqual(len(tree), 2,
                         "Expected 2 comments for this node")
        self.assertEqual(len(tree[0]['children']), 2,
                         "Expected 2 replies to first comment")
        self.assertEqual(len(tree[0]['children'][0]['children']), 0,
                         "Expected no replies to first comment reply")
        self.assertEqual(len(tree[0]['children'][1]['children']), 1,
                         "Expected 1 reply to second comment reply")

    def test_private_tree(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_2.refresh_from_db()
        print(self.root_2.get_descendant_count())
        print(self.root_2.get_children_count())
        tree = TreeComment.tree_from_comment(self.root_2)
        self.assertEqual(len(tree), 2,
                         "Expected 2 comments for this node")
        self.assertEqual(len(tree[0]['children']), 0,
                         "Expected 0 public replies to first comment")
        self.assertEqual(len(tree[1]['children'][1]['children']), 1,
                         "Expected 1 reply to second comment reply")

    def test_public_filter(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_2.refresh_from_db()
        print(self.root_2.get_descendant_count())
        print(self.root_2.get_children_count())
        tree = TreeComment.tree_from_comment(self.root_2, filter_public=False)
        self.assertEqual(len(tree), 2,
                         "Expected 2 comments for this node")
        self.assertEqual(len(tree[0]['children']), 2,
                         "Expected 2 replies to first comment")
        self.assertEqual(len(tree[0]['children'][0]['children']), 0,
                         "Expected no replies to first comment reply")
        self.assertEqual(len(tree[0]['children'][1]['children']), 1,
                         "Expected 1 reply to second comment reply")

    @skip('Not ready yet')
    def test_filter_old_messages(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_1.refresh_from_db()
        print(self.root_1.get_descendant_count())
        print(self.root_1.get_children_count())
        tree = TreeComment.tree_from_comment(self.root_1,
                                             filter_public=False,
                                             start=utime(20),
                                             end=utime(2))

        self.assertEqual(len(tree), 1,
                         "Expected 2 comments for this node")
        self.assertEqual(len(tree[0]['children']), 0,
                         "Expected one reply to first comment")
        self.assertEqual(len(tree[1]['children']), 2,
                         "Expected 2 replies to second comment")
        self.assertEqual(len(tree[0]['children'][0]['children']), 0,
                         "Expected 1 replies to first comment reply")
        self.assertEqual(len(tree[0]['children'][0]['children']), 1,
                         "Expected 1 replies to first comment reply")

    @skip('Not ready yet')
    def test_filter_new_messages(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_1.refresh_from_db()
        print(self.root_1.get_descendant_count())
        print(self.root_1.get_children_count())
        now = timezone.now()
        tree = TreeComment.tree_from_comment(self.root_1,
                                             filter_public=False,
                                             start=now - timezone.timedelta(days=2),
                                             end=now)

        self.assertEqual(len(tree), 1,
                         "Expected 2 comments for this node")
        self.assertEqual(len(tree[0]['children']), 1,
                         "Expected 2 replies to first comment")
        self.assertEqual(len(tree[0]['children'][0]['children']), 1,
                         "Expected no replies to first comment reply")


class TestTreeCommentPerformance(ArticleBaseTestCase):

    def setUp(self):
        super().setUp()
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site1 = Site.objects.get(pk=1)
        self.site2 = Site.objects.create(domain='site2.com', name='site2.com')

        self.root_1 = TreeComment.objects.get_or_create_root(self.article_1)
        self.root_1_pk = self.root_1.pk
        self.root_2 = TreeComment.objects.get_or_create_root(
            self.article_1, site=self.site2)
        self.root_2_pk = self.root_2.pk

        r1 = TreeComment.objects.get(pk=self.root_1_pk)

        make_lots_of_comments(r1, count=4, depth=4)

    def test_unfiltered_tree(self):
        # there is no comment posted yet to article_1 nor article_2
        self.root_1.refresh_from_db()
        cnt = self.root_1.get_descendant_count()

        data = TreeComment.structured_tree_data(self.root_1)
        print(f"Comment: {data.get('comment')}")
        print(f"Tree: {data.get('hierarchy')}")
        tree = data.get('hierarchy')

        self.assertEqual(cnt, len(data.get('comments')),
                         "Expected count to match")
        n_children = self.root_1.get_children_count()
        self.assertEqual(n_children, len(tree),
                         "Expected tree to have matching children")
