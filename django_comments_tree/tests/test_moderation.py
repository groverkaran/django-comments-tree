from __future__ import unicode_literals

import re

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from datetime import datetime, timedelta

import django
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase, RequestFactory
from django.urls import reverse

from django_comments_tree.models import TreeCommentFlag

from django_comments_tree import django_comments
from django_comments_tree.views import comments as views
from django_comments_tree.models import LIKEDIT_FLAG, DISLIKEDIT_FLAG
from django_comments_tree.tests.models import Diary
from django_comments_tree.tests.test_views import (confirm_comment_url,
                                                   post_diary_comment)


request_factory = RequestFactory()


send_mail = ''  # string to send_mail function to patch
try:
    import importlib
    cmod = importlib.util.find_spec('django_comments_tree')
    importlib.util.module_from_spec(cmod)
    send_mail = 'django_comments_tree.moderation.send_mail'
except ImportError:
    send_mail = 'django.contrib.comments.moderation.send_mail'


class ModeratorApprovesComment(TestCase):
    def setUp(self):
        patcher_app1 = patch(send_mail)
        patcher_app2 = patch('django_comments_tree.views.comments.send_mail')
        self.mailer_app1 = patcher_app1.start()
        self.mailer_app2 = patcher_app2.start()
        self.diary_entry = Diary.objects.create(
            body="What I did on October...",
            allow_comments=True,
            publish=datetime.now())
        self.form = django_comments.get_form()(self.diary_entry)

    def post_valid_data(self, auth_user=None):
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(self.form.initial)
        response = post_diary_comment(data, self.diary_entry, auth_user=auth_user)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))

    def test_moderation_with_registered_user(self):
        user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.assertEqual(self.mailer_app1.call_count, 0)
        self.post_valid_data(user)
        
        # Moderation class:
        # django_comments_tree.tests.models.DiaryCommentModerator
        # must trigger an email once comment has passed moderation.
        self.assertEqual(self.mailer_app1.call_count, 1)
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        self.assertTrue(comment.is_public)

    def test_moderation_with_unregistered_user(self):
        self.post_valid_data()
        self.assertEqual(self.mailer_app1.call_count, 0)
        self.assertEqual(self.mailer_app2.call_count, 1)
        mail_msg = self.mailer_app2.call_args[0][1]
        key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                            mail_msg).group("key"))
        confirm_comment_url(key)
        self.assertEqual(self.mailer_app1.call_count, 1)
        self.assertEqual(self.mailer_app2.call_count, 1)
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        self.assertTrue(comment.is_public)


class ModeratorHoldsComment(TestCase):
    def setUp(self):
        patcher_app1 = patch(send_mail)
        patcher_app2 = patch('django_comments_tree.views.comments.send_mail')
        self.mailer_app1 = patcher_app1.start()
        self.mailer_app2 = patcher_app2.start()
        self.diary_entry = Diary.objects.create(
            body="What I did Yesterday...",
            allow_comments=True,
            publish=datetime.now() - timedelta(days=5))
        self.form = django_comments.get_form()(self.diary_entry)

    def post_valid_data(self, auth_user=None):
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(self.form.initial)
        response = post_diary_comment(data, self.diary_entry, auth_user=auth_user)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/comments/posted/?c='))

    def test_moderation_with_registered_user(self):
        user = User.objects.create_user("bob", "bob@example.com", "pwd")
        self.assertEqual(self.mailer_app1.call_count, 0, f"Expected value to be {0}")
        self.post_valid_data(user)
        # Moderation class:
        # django_comments_tree.tests.models.DiaryCommentModerator
        # must trigger an email once comment has passed moderation.
        self.assertEqual(self.mailer_app1.call_count, 1, f"Expected value to be {1}")
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        self.assertFalse(comment.is_public)

    def test_moderation_with_unregistered_user(self):
        self.post_valid_data()
        self.assertEqual(self.mailer_app1.call_count, 0, f"Expected value to be 0")
        self.assertEqual(self.mailer_app2.call_count, 1, f"Expected value to be 1")
        mail_msg = self.mailer_app2.call_args[0][1]
        key = str(re.search(r'http://.+/confirm/(?P<key>[\S]+)/',
                            mail_msg).group("key"))
        confirm_comment_url(key)
        self.assertEqual(self.mailer_app1.call_count, 1, f"Expected value to be 1")
        self.assertEqual(self.mailer_app2.call_count, 1, f"Expected value to be 1")
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        self.assertFalse(comment.is_public)


class FlaggingRemovalSuggestion(TestCase):
    """Scenario to test the flag removal_suggestion_notification"""

    def setUp(self):
        patcher = patch('django_comments_tree.moderation.send_mail')
        self.mailer = patcher.start()
        diary_entry = Diary.objects.create(
            body="What I did on October...",
            allow_comments=True,
            publish=datetime.now())
        form = django_comments.get_form()(diary_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(form.initial)
        post_diary_comment(data, diary_entry, auth_user=self.user)

    def test_anonymous_user_redirected_when_flagging(self):
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        flag_url = reverse("comments-flag", args=[comment.id])
        request = request_factory.get(flag_url)
        request.user = AnonymousUser()
        response = views.FlagView.as_view()(request, comment.id)
        dest_url = '/accounts/login/?next=/comments/flag/2/'
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, dest_url)

    def test_loggedin_user_can_flag_comment(self):
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        flag_url = reverse("comments-flag", args=[comment.id])
        request = request_factory.get(flag_url)
        request.user = self.user
        response = views.FlagView.as_view()(request, comment.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b'Flag comment') > -1)
        request = request_factory.post(flag_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.FlagView.as_view()(request, comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("comments-flag-done") + "?c=2")
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=TreeCommentFlag.SUGGEST_REMOVAL)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")

    def test_email_is_triggered(self):
        flag_url = reverse("comments-flag", args=[1])
        self.assertEqual(self.mailer.call_count, 1, f"Expected mailer was not called yet")
        request = request_factory.post(flag_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        views.FlagView.as_view()(request, 1)
        self.assertEqual(self.mailer.call_count, 2,
                         f"Expected mailer to have been called 1 more time")


class FlaggingLikedItAndDislikedIt(TestCase):
    """Scenario to test the flag removal_suggestion_notification"""

    def setUp(self):
        diary_entry = Diary.objects.create(
            body="What I did on October...",
            allow_comments=True,
            publish=datetime.now())
        form = django_comments.get_form()(diary_entry)
        self.user = User.objects.create_user("bob", "bob@example.com", "pwd")
        data = {"name": "Bob", "email": "bob@example.com", "followup": True,
                "reply_to": 0, "level": 1, "order": 1,
                "comment": "Es war einmal eine kleine..."}
        data.update(form.initial)
        post_diary_comment(data, diary_entry, auth_user=self.user)

    def test_anonymous_user_is_redirected(self):
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        # Like it.
        like_url = reverse("comments-tree-like", args=[comment.id])
        request = request_factory.get(like_url)
        request.user = AnonymousUser()
        response = views.like(request, comment.id)
        dest_url = '/accounts/login/?next=/comments/like/2/'
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, dest_url)
        # Dislike it.
        dislike_url = reverse("comments-tree-dislike", args=[comment.id])
        request = request_factory.get(dislike_url)
        request.user = AnonymousUser()
        response = views.dislike(request, comment.id)
        dest_url = '/accounts/login/?next=/comments/dislike/2/'
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, dest_url)

    def test_loggedin_user_can_like(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        like_url = reverse("comments-tree-like", args=[comment.id])
        request = request_factory.get(like_url)
        request.user = self.user
        response = views.like(request, comment.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b'value="I like it"') > -1)
        request = request_factory.post(like_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.like(request, comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         reverse("comments-tree-like-done") + "?c=2")
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")

    def test_loggedin_user_can_dislike(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        dislike_url = reverse("comments-tree-dislike", args=[comment.id])
        request = request_factory.get(dislike_url)
        request.user = self.user
        response = views.dislike(request, comment.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.find(b'value="I dislike it"') > -1)
        request = request_factory.post(dislike_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.dislike(request, comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         reverse("comments-tree-dislike-done") + "?c=2")
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")

    def test_likedit_can_be_cancelled(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        like_url = reverse("comments-tree-like", args=[comment.id])
        request = request_factory.post(like_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.like(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")
        # Now we liked the comment again to cancel the flag.
        response = views.like(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 0, f"Expected value to be 0")

    def test_dislikedit_can_be_cancelled(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        dislike_url = reverse("comments-tree-dislike", args=[comment.id])
        request = request_factory.post(dislike_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.dislike(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")
        # Now we liked the comment again to cancel the flag.
        response = views.dislike(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 0, f"Expected value to be 0")

    def test_likedit_cancels_dislikedit(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        dislike_url = reverse("comments-tree-dislike", args=[comment.id])
        request = request_factory.post(dislike_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.dislike(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")
        # Now we liked the comment again to cancel the flag.
        like_url = reverse("comments-tree-like", args=[comment.id])
        request = request_factory.post(like_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.like(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 0, f"Expected value to be 0")
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")

    def test_dislikedit_cancels_likedit(self):
        if django.VERSION < (1, 5):
            return
        comment = django_comments.get_model()\
                                 .objects.for_app_models('tests.diary')[0]
        like_url = reverse("comments-tree-like", args=[comment.id])
        request = request_factory.post(like_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.like(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")
        # Now we liked the comment again to cancel the flag.
        dislike_url = reverse("comments-tree-dislike", args=[comment.id])
        request = request_factory.post(dislike_url)
        request.user = self.user
        request._dont_enforce_csrf_checks = True
        response = views.dislike(request, comment.id)
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=LIKEDIT_FLAG)
        self.assertEqual(flags.count(), 0, f"Expected value to be 0")
        flags = TreeCommentFlag.objects.filter(comment=comment,
                                           user=self.user,
                                           flag=DISLIKEDIT_FLAG)
        self.assertEqual(flags.count(), 1, f"Expected value to be 1")
