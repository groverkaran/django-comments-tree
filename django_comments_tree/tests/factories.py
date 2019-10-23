from django.contrib.gis.geos import GEOSGeometry

import factory
import django_comments_tree.models as models
import django_comments_tree.tests.models as tmodels
from django.contrib.auth.models import User
from django.utils.text import slugify


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"username{n}")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('first_name')
    email = factory.Faker('email')


class ArticleFactory(factory.DjangoModelFactory):
    class Meta:
        model = tmodels.Article

    title = factory.Sequence(lambda n: f"Article Title {n}")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.title))
    body = factory.Faker('paragraphs', nb=3)


class DiaryFactory(factory.DjangoModelFactory):
    class Meta:
        model = tmodels.Diary
    body = factory.Faker('paragraphs', nb=3)


class CommentAssociationFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.CommentAssociation


class TreeCommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.TreeComment


class TreeCommentFlagFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.TreeCommentFlag

    flag = ""
