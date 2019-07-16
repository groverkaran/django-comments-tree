from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _, ungettext

from django_comments_tree import get_model
from django_comments_tree.views.moderation import perform_flag, perform_approve, perform_delete
from django_comments_tree.models import TreeComment, BlackListedDomain, TreeCommentFlag


class UsernameSearch(object):
    """The User object may not be auth.User, so we need to provide
    a mechanism for issuing the equivalent of a .filter(user__username=...)
    search in CommentAdmin.
    """

    def __str__(self):
        return 'user__%s' % get_user_model().USERNAME_FIELD


class CommentsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            _('Content'),
            {'fields': ('user', 'user_name', 'user_email', 'user_url', 'comment')}
        ),
        (
            _('Metadata'),
            {'fields': ('submit_date', 'updated_on', 'ip_address', 'is_public', 'is_removed')}
        ),
    )

    list_display = ('name', 'ip_address', 'submit_date', 'is_public', 'is_removed')
    list_filter = ('submit_date', 'site', 'is_public', 'is_removed')
    date_hierarchy = 'submit_date'
    ordering = ('-submit_date',)
    raw_id_fields = ('user',)
    search_fields = ('comment', UsernameSearch(), 'user_name',
                     'user_email', 'user_url', 'ip_address')
    actions = ["flag_comments", "approve_comments", "remove_comments"]

    def get_actions(self, request):
        actions = super(CommentsAdmin, self).get_actions(request)
        # Only superusers should be able to delete the comments from the DB.
        if not request.user.is_superuser and 'delete_selected' in actions:
            actions.pop('delete_selected')
        if not request.user.has_perm('django_comments.can_moderate'):
            if 'approve_comments' in actions:
                actions.pop('approve_comments')
            if 'remove_comments' in actions:
                actions.pop('remove_comments')
        return actions

    def flag_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_flag,
                        lambda n: ungettext('flagged', 'flagged', n))

    flag_comments.short_description = _("Flag selected comments")

    def approve_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_approve,
                        lambda n: ungettext('approved', 'approved', n))

    approve_comments.short_description = _("Approve selected comments")

    def remove_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_delete,
                        lambda n: ungettext('removed', 'removed', n))

    remove_comments.short_description = _("Remove selected comments")

    def _bulk_flag(self, request, queryset, action, done_message):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_comments = 0
        for comment in queryset:
            action(request, comment)
            n_comments += 1

        msg = ungettext('%(count)s comment was successfully %(action)s.',
                        '%(count)s comments were successfully %(action)s.',
                        n_comments)
        self.message_user(request, msg % {'count': n_comments, 'action': done_message(n_comments)})


class TreeCommentsAdmin(CommentsAdmin):
    list_display = ('cid', 'name',
                    'ip_address', 'submit_date', 'followup', 'is_public',
                    'is_removed')
    list_display_links = ('cid',)
    list_filter = ('is_public', 'is_removed', 'followup')
    fieldsets = (
        ('Content', {'fields': ('user', 'user_name', 'user_email',
                                'user_url', 'comment', 'followup')}),
        ('Metadata', {'fields': ('submit_date', 'ip_address',
                                 'is_public', 'is_removed')}),
    )
    date_hierarchy = 'submit_date'
    ordering = ('submit_date',)
    search_fields = ['object_id', 'user__username', 'user_name', 'user_email',
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
