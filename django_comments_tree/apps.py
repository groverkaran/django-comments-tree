from django.apps import AppConfig


class CommentsTreeConfig(AppConfig):
    name = 'django_comments_tree'
    verbose_name = 'Comments Tree'

    def get_models(self, *args, **kwargs):
        return super().get_models(*args, **kwargs)
