from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow owners or admins to edit"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user or request.user.is_staff


class IsAdmin(permissions.BasePermission):
    """Allow only admin users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsSeller(permissions.BasePermission):
    """Allow only sellers and admins"""
    
    def has_permission(self, request, view):
        return request.user and (request.user.user_type in ['seller', 'admin'])


class IsCustomer(permissions.BasePermission):
    """Allow only customers"""
    
    def has_permission(self, request, view):
        return request.user and request.user.user_type == 'customer'