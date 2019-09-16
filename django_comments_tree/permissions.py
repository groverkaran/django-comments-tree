from django.contrib.auth import get_user

from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return get_user(request) == obj.user


class IsModerator(BasePermission):

    def has_permission(self, request, view):
        return request.user.has_perm('django_comments.can_moderate')
