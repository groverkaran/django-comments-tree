from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from django_comments_tree.admin import TreeCommentsAdmin
from custom.mycomments.models import MyComment


class MyCommentAdmin(TreeCommentsAdmin):
    list_display = ('title', 'name',
                    'object_pi', 'submit_date', 'followup', 'is_public',
                    'is_removed')
    list_display_links = ('cid', 'title')
    fieldsets = (
        (_('Content'),  {'fields': ('title', 'user', 'user_name', 'user_email',
                                    'user_url', 'comment', 'followup')}),
        (_('Metadata'), {'fields': ('submit_date', 'ip_address',
                                    'is_public', 'is_removed')}),
    )

admin.site.register(MyComment, MyCommentAdmin)
    
