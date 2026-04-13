from rest_framework.permissions import BasePermission, SAFE_METHODS

ROLE_RANK = {
    'superadmin': 7,
    'org_admin':  6,
    'hr_manager': 5,
    'manager':    4,
    'teacher':    3,
    'employee':   2,
    'student':    1,
}


def rank(user):
    return ROLE_RANK.get(getattr(user, 'role', ''), 0)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'superadmin'


class IsOrgAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and rank(request.user) >= ROLE_RANK['org_admin']


class IsHROrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and rank(request.user) >= ROLE_RANK['hr_manager']


class IsManagerOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and rank(request.user) >= ROLE_RANK['manager']


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsSameOrg(BasePermission):
    """Objects must belong to the request user's organization."""
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'superadmin':
            return True
        user_org = request.user.organization_id
        if hasattr(obj, 'organization_id'):
            return obj.organization_id == user_org
        if hasattr(obj, 'employee') and hasattr(obj.employee, 'organization_id'):
            return obj.employee.organization_id == user_org
        return False


class IsOwnerOrManagerAbove(BasePermission):
    """Allow the owner of the resource or any manager-level user."""
    def has_object_permission(self, request, view, obj):
        if rank(request.user) >= ROLE_RANK['manager']:
            return True
        employee = getattr(obj, 'employee', None)
        return employee == request.user or obj == request.user


class ReadOnlyOrManagerAbove(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and rank(request.user) >= ROLE_RANK['manager']
