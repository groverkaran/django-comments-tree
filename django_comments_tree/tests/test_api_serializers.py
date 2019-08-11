import json

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import TestCase

from django_comments_tree.api.serializers import (APICommentSerializer,
                                                  WriteCommentSerializer)
from django_comments_tree.models import (TreeComment)
from django_comments_tree.tests.models import Article
from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework.test import APIRequestFactory, force_authenticate


class TestSerializerBase(TestCase):

    def setUp(self):
        super().setUp()

        self.request_factory = APIRequestFactory()

        self.article = Article.objects.create(
            title="September", slug="september", body="During September...")
        self.article_ct = ContentType.objects.get(app_label="tests",
                                                  model="article")

        self.site = Site.objects.get(pk=1)

        self.root = TreeComment.objects.get_or_create_root(self.article)

        self.comment = self.root.add_child(comment="just a testing comment")
        self.user = User.objects.create_user("bob", "", "pwd")

    def get_request(self, url, data):
        request = self.request_factory.post(url, data)

        if self.user:
            force_authenticate(request, user=self.user)
        return request


class TestApiSerializer(TestSerializerBase):

    def test_serialize_data(self):
        """ Serialize some data, make sure it works """

        serializer = APICommentSerializer(self.comment)
        self.assertTrue(serializer.is_valid)

    def test_serializer_render(self):

        serializer = APICommentSerializer(self.comment,
                                          context={'request': None})
        rendered = json.dumps(serializer.data)
        self.assertIsNotNone(rendered)

    def test_serializer_save(self):
        url = reverse('comments-post-comment')
        request = self.get_request(url, {})
        serializer = APICommentSerializer(self.comment,
                                          data={'comment': 'comment value',
                                                'comment.rendered': '<p>value</p>',
                                                },
                                          context={'request': request}
                                          )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.comment.refresh_from_db()
        c = TreeComment.objects.get(pk=self.comment.pk)
        self.assertEqual(c.comment.raw, 'comment value')


class TestWriteSerializer(TestSerializerBase):

    def test_write_serialize(self):
        """ Serialize some data, make sure it works """

        url = reverse('comments-post-comment')
        request = self.get_request(url, {})

        serializer = WriteCommentSerializer(self.comment,
                                            context={'request': request})
        self.assertTrue(serializer.is_valid)

    def test_write_serializer_save(self):
        """ This is a big method to test """

