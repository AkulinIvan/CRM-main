from functools import lru_cache
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

from accounts.models import User

class RolePermissionMixin(UserPassesTestMixin):
    """Base mixin for role-based permissions"""
    allowed_roles = []
    
    @lru_cache(maxsize=128)
    def test_func(self):
        return self.request.user.role in self.allowed_roles
    
    def handle_no_permission(self):
        raise PermissionDenied(
            f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
        )

class AdminRequiredMixin(RolePermissionMixin):
    allowed_roles = [User.Role.ADMIN]

class CoordinatorRequiredMixin(RolePermissionMixin):
    allowed_roles = [User.Role.ADMIN, User.Role.COORDINATOR]

class DispatcherRequiredMixin(RolePermissionMixin):
    allowed_roles = [
        User.Role.ADMIN, 
        User.Role.COORDINATOR, 
        User.Role.DISPATCHER
    ]

class MasterRequiredMixin(RolePermissionMixin):
    allowed_roles = [
        User.Role.ADMIN, 
        User.Role.COORDINATOR, 
        User.Role.MASTER
    ]

class ExecutorRequiredMixin(RolePermissionMixin):
    allowed_roles = [
        User.Role.ADMIN, 
        User.Role.COORDINATOR, 
        User.Role.EXECUTOR
    ]

# Decorator versions
def admin_required(view_func):
    return user_passes_test(
        lambda u: u.role == User.Role.ADMIN,
        login_url='accounts:login'
    )(view_func)

def coordinator_required(view_func):
    return user_passes_test(
        lambda u: u.role in [User.Role.ADMIN, User.Role.COORDINATOR],
        login_url='accounts:login'
    )(view_func)