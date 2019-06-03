from __future__ import unicode_literals

from django.contrib import admin

from django_comments import get_model
from django_comments.admin import CommentsAdmin
from django_comments_tree.models import TreeComment, BlackListedDomain, TreeCommentFlag


class TreeCommentsAdmin(CommentsAdmin):
    list_display = ('thread_level', 'cid', 'name', 'content_type', 'object_pk',
                    'ip_address', 'submit_date', 'followup', 'is_public',
                    'is_removed')
    list_display_links = ('cid',)
    list_filter = ('content_type', 'is_public', 'is_removed', 'followup')
    fieldsets = (
        (None, {'fields': ('content_type', 'object_pk', 'site')}),
        ('Content', {'fields': ('user', 'user_name', 'user_email',
                                'user_url', 'comment', 'followup')}),
        ('Metadata', {'fields': ('submit_date', 'ip_address',
                                 'is_public', 'is_removed')}),
    )
    date_hierarchy = 'submit_date'
    ordering = ('submitted_date')
    search_fields = ['object_pk', 'user__username', 'user_name', 'user_email',
                     'comment']

    def thread_level(self, obj):
        rep = '|'
        if obj.level:
            rep += '-' * obj.level
            rep += " c%d to c%d" % (obj.id, obj.parent_id)
        else:
            rep += " c%d" % obj.id
        return rep

    def cid(self, obj):
        return 'c%d' % obj.id


class BlackListedDomainAdmin(admin.ModelAdmin):
    search_fields = ['domain']


if get_model() is TreeComment:
    admin.site.register(TreeComment, TreeCommentsAdmin)
    admin.site.register(TreeCommentFlag)
    admin.site.register(BlackListedDomain, BlackListedDomainAdmin)
