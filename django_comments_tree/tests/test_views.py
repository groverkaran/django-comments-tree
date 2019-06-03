from __future__ import unicode_literals

import re
import random
import string
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from datetime import datetime

# from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.auth.models import AnonymousUser, User
from django.http.response import Http404
from django.test import TestCase, RequestFactory
from django.urls import reverse

from django_comments_tree.views.comments import CommentView
    
from django_comments_tree import signals, signed, get_form
from django_comments_tree.views import comments as views
from django_comments_tree.conf import settings
from django_comments_tree.models import TreeComment
from django_comments_tree.tests.models import Article, Diary


request_factory = RequestFactory()


def post_article_comment(data, article, auth_user=None):
    request = request_factory.post(
        reverse('article-detail', kwargs={'year': article.publish.year,
                                          'month': article.publish.month,
                                          'day': article.publish.day,
                                          'slug': article.slug}),
        data=data, follow=True)
    if auth_user:
        request.user = auth_user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return CommentView.as_view()(request)


def post_diary_comment(data, diary_entry, auth_user=None):
    request = request_factory.post(
        reverse('diary-detail', kwargs={'year': diary_entry.publish.year,
                                        'month': diary_entry.publish.month,
                                        'day': diary_entry.publish.day}),
        data=data, follow=True)
    if auth_user:
        request.user = auth_user
    else:
        request.user = AnonymousUser()
    request._dont_enforce_csrf_checks = True
    return CommentView.as_view()(request)


def confirm_comment_url(key, follow=True):
    request = request_factory.get(reverse("comments-tree-confirm",
                                          kwargs={'key': key}),
                                  follow=follow)
    request.user = AnonymousUser()
    return views.confirm(request, key)


class OnCommentWasPostedTestCase(TestCase):
    def setUp(self):
        patcher = patch('django_comments_tree.views.comments.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="October", slug="october", body="What I did on October...")
        self.form = get_form()(self.article)
        self.factory = RequestFactory()
        self.user = AnonymousUser()

    def post_valid_data(self, auth_user=None):
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article, auth_user)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))

    def test_post_as_authenticated_user(self):
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_valid_data(self.user)
        # no confirmation email sent as user is authenticated
        self.assertTrue(self.mock_mailer.call_count == 0)

    def test_confirmation_email_is_sent(self):
        self.assertTrue(self.mock_mailer.call_count == 0)
        self.post_valid_data()
        self.assertTrue(self.mock_mailer.call_count == 1)
        self.user = AnonymousUser()


class ConfirmCommentTestCase(TestCase):
    def setUp(self):
        patcher = patch('django_comments_tree.views.comments.send_mail')
        self.mock_mailer = patcher.start()
        # Create random string so that it's harder for zlib to compress
        content = ''.join(random.choice(string.printable) for _ in range(6096))
        self.article = Article.objects.create(title="September",
                                              slug="september",
                                              body="In September..." + content)
        self.form = get_form()(self.article)
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal iene kleine..."}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertTrue(self.mock_mailer.call_count == 1)
        self.key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                                 self.mock_mailer.call_args[0][1]).group("key"))
        self.addCleanup(patcher.stop)

    def test_confirm_url_is_short_enough(self):
        # Tests that the length of the confirm url's length isn't
        # dependent on the article length.
        l = len(reverse("comments-tree-confirm",
                        kwargs={'key': self.key}))
        # print("\nXXXXXXXXXXX:", l)
        self.assertLessEqual(l, 4096, "Urls can only be a max of 4096")

    def test_404_on_bad_signature(self):
        with self.assertRaises(Http404):
            confirm_comment_url(self.key[:-1])

    def test_consecutive_confirmation_url_visits_fail(self):
        # test that consecutives visits to the same confirmation URL produce
        # an Http 404 code, as the comment has already been verified in the
        # first visit
        confirm_comment_url(self.key)
        with self.assertRaises(Http404):
            confirm_comment_url(self.key)

    def test_signal_receiver_may_discard_the_comment(self):
        # test that receivers of signal confirmation_received may return False
        # and thus rendering a template_discarded output
        def on_signal(sender, comment, request, **kwargs):
            return False

        self.assertEqual(self.mock_mailer.call_count, 1)  # sent during setUp
        signals.confirmation_received.connect(on_signal)
        response = confirm_comment_url(self.key)
        # mailing avoided by on_signal:
        self.assertEqual(self.mock_mailer.call_count, 1)
        self.assertTrue(response.content.find(b'Comment discarded') > -1)

    def test_comment_is_created_and_view_redirect(self):
        # testing that visiting a correct confirmation URL creates a TreeComment
        # and redirects to the article detail page
        Site.objects.get_current().domain = "testserver"  # django bug #7743
        response = confirm_comment_url(self.key, follow=False)
        data = signed.loads(self.key, extra_key=settings.COMMENTS_TREE_SALT)
        try:
            comment = TreeComment.objects.get(
                user_name=data["user_name"],
                user_email=data["user_email"],
                submit_date=data["submit_date"])
        except:
            comment = None
        self.assertTrue(comment is not None)
        self.assertEqual(response.url, comment.get_absolute_url())

    def test_notify_comment_followers(self):
        # send a couple of comments to the article with followup=True and check
        # that when the second comment is confirmed a followup notification
        # email is sent to the user who sent the first comment
        self.assertEqual(self.mock_mailer.call_count, 1)
        confirm_comment_url(self.key)
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send 2nd comment
        self.form = get_form()(self.article)
        data = {"name": "Alice", "email": "alice@example.com",
                "followup": True, "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(self.form.initial)
        response = post_article_comment(data, article=self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                             self.mock_mailer.call_args[0][1]).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.assertTrue(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assertTrue(self.mock_mailer.call_args[0][1].find(
            "There is a new comment following up yours.") > -1)

    def test_notify_followers_dupes(self):
        # first of all confirm Bob's comment otherwise it doesn't reach DB
        confirm_comment_url(self.key)
        # then put in play pull-request-15's assert...
        # https://github.com/sharpertool/django-comments-tree/pull/15
        diary = Diary.objects.create(
            body='Lorem ipsum',
            allow_comments=True
        )
        self.assertEqual(diary.pk, self.article.pk)

        self.form = get_form()(diary)
        data = {"name": "Charlie", "email": "charlie@example.com",
                "followup": True, "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(self.form.initial)
        response = post_diary_comment(data, diary_entry=diary)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                                 self.mock_mailer.call_args[0][1]).group("key"))
        # 1) confirmation for Bob (sent in `setUp()`)
        # 2) confirmation for Charlie
        self.assertEqual(self.mock_mailer.call_count, 2)
        response = confirm_comment_url(self.key)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/cr/'))
        self.assertEqual(self.mock_mailer.call_count, 2)

        self.form = get_form()(self.article)
        data = {"name": "Alice", "email": "alice@example.com",
                "followup": True, "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal iene kleine..."}
        data.update(self.form.initial)
        response = post_article_comment(data, article=self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.assertEqual(self.mock_mailer.call_count, 3)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                             self.mock_mailer.call_args[0][1]).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 4)
        self.assertTrue(self.mock_mailer.call_args[0][3] == ["bob@example.com"])
        self.assertTrue(self.mock_mailer.call_args[0][1].find(
            "There is a new comment following up yours.") > -1)

    def test_no_notification_for_same_user_email(self):
        # test that a follow-up user_email don't get a notification when
        # sending another email to the thread
        self.assertEqual(self.mock_mailer.call_count, 1)
        confirm_comment_url(self.key)  # confirm Bob's comment
        # no comment followers yet:
        self.assertEqual(self.mock_mailer.call_count, 1)
        # send Bob's 2nd comment
        self.form = get_form()(self.article)
        data = {"name": "Alice", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Bob's comment he shouldn't get notified about"}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(self.mock_mailer.call_count, 2)
        self.key = re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                             self.mock_mailer.call_args[0][1]).group("key")
        confirm_comment_url(self.key)
        self.assertEqual(self.mock_mailer.call_count, 2)


class ReplyNoCommentTestCase(TestCase):
    def test_reply_non_existing_comment_raises_404(self):
        response = self.client.get(reverse("comments-tree-reply",
                                           kwargs={"cid": 1}))
        self.assertContains(response, "404", status_code=404)


class ReplyCommentTestCase(TestCase):
    def setUp(self):
        article = Article.objects.create(title="September",
                                         slug="september",
                                         body="What I did on September...")
        article_ct = ContentType.objects.get(app_label="tests", model="article")
        site = Site.objects.get(pk=1)

        root = TreeComment.objects.get_or_create_root(article)

        c1 = root.add_child(comment="comment 1 to article")
        r1 = c1.add_child(comment="comment 1 to comment 1")
        rr1 = r1.add_child(comment="comment 1 to comment 1")

        self.deep_reply = rr1

    def test_not_allow_threaded_reply_raises_403(self):
        response = self.client.get(reverse("comments-tree-reply",
                                           kwargs={"cid": self.deep_reply.id}))
        self.assertEqual(response.status_code, 403)


class MuteFollowUpsTestCase(TestCase):

    def setUp(self):
        # Creates an article and send two comments to the article with follow-up
        # notifications. First comment doesn't have to send any notification.
        # Second comment has to send one notification (to Bob).
        self.factory = RequestFactory()
        patcher = patch('django_comments_tree.views.comments.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September")
        self.form = get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Nice September you had..."}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.assertTrue(self.mock_mailer.call_count == 1)
        bobkey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                               self.mock_mailer.call_args[0][1]).group("key"))
        confirm_comment_url(bobkey)  # confirm Bob's comment

        # Alice sends 2nd comment to the article with follow-up
        data = {"name": "Alice", "email": "alice@example.com",
                "followup": True, "reply_to": 1, "level": 1, "order": 1,
                "comment": "Yeah, great photos"}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.assertTrue(self.mock_mailer.call_count == 2)
        alicekey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                                 self.mock_mailer.call_args[0][1]).group("key"))
        confirm_comment_url(alicekey)  # confirm Alice's comment

        # Bob receives a follow-up notification
        self.assertTrue(self.mock_mailer.call_count == 3)
        self.bobs_mutekey = str(re.search(
            r'http://.+/mute/(?P<key>[\S]+)/',
            self.mock_mailer.call_args[0][1]).group("key"))
        self.addCleanup(patcher.stop)

    def get_mute_followup_url(self, key):
        request = self.factory.get(reverse("comments-tree-mute",
                                           kwargs={'key': key}),
                                   follow=True)
        request.user = AnonymousUser()
        response = views.mute(request, key)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b'Comment thread muted') > -1)
        return response

    def test_mute_followup_notifications(self):
        # Bob's receive a notification and click on the mute link to
        # avoid additional comment messages on the same article.
        self.get_mute_followup_url(self.bobs_mutekey)
        # Alice sends 3rd comment to the article with follow-up
        data = {"name": "Alice", "email": "alice@example.com",
                "followup": True, "reply_to": 2, "level": 1, "order": 1,
                "comment": "And look at this and that..."}
        data.update(self.form.initial)
        response = post_article_comment(data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        # Alice confirms her comment...
        self.assertTrue(self.mock_mailer.call_count == 4)
        alicekey = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                                 self.mock_mailer.call_args[0][1]).group("key"))
        confirm_comment_url(alicekey)  # confirm Alice's comment
        # Alice confirmed her comment, but this time Bob won't receive any
        # notification, neither do Alice being the sender
        self.assertTrue(self.mock_mailer.call_count == 4)


class HTMLDisabledMailTestCase(TestCase):
    def setUp(self):
        # Create an article and send a comment. Test method will chech headers
        # to see wheter messages has multiparts or not.
        patcher = patch('django_comments_tree.views.comments.send_mail')
        self.mock_mailer = patcher.start()
        self.article = Article.objects.create(
            title="September", slug="september", body="John's September")
        self.form = get_form()(self.article)

        # Bob sends 1st comment to the article with follow-up
        self.data = {"name": "Bob", "email": "bob@example.com",
                     "followup": True, "reply_to": 0, "level": 1, "order": 1,
                     "comment": "Nice September you had..."}
        self.data.update(self.form.initial)

    @patch.multiple('django_comments_tree.conf.settings',
                    COMMENTS_TREE_SEND_HTML_EMAIL=False)
    def test_mail_does_not_contain_html_part(self):
        with patch.multiple('django_comments_tree.conf.settings',
                            COMMENTS_TREE_SEND_HTML_EMAIL=False):
            response = post_article_comment(self.data, self.article)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/comments/posted/?c='))
            self.assertTrue(self.mock_mailer.call_count == 1)
            self.assertTrue(self.mock_mailer.call_args[1]['html'] is None)

    def test_mail_does_contain_html_part(self):
        response = post_article_comment(self.data, self.article)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))
        self.assertTrue(self.mock_mailer.call_count == 1)
        self.assertTrue(self.mock_mailer.call_args[1]['html'] is not None)
