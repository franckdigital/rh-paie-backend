from rest_framework.permissions import BasePermission

METHOD_ACTION = {
    'GET': 'view',
    'HEAD': 'view',
    'OPTIONS': 'view',
    'POST': 'create',
    'PUT': 'edit',
    'PATCH': 'edit',
    'DELETE': 'delete',
}

SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})


def _employe_of(user):
    try:
        return user.employe
    except Exception:
        return None


def _employe_pk_of_obj(obj):
    """Return the PK of the Employe linked to obj, or None."""
    emp = getattr(obj, 'employe', None)
    if emp is None:
        return None
    return emp if isinstance(emp, int) else getattr(emp, 'pk', None)


class RBACPermission(BasePermission):
    """
    Permission based on User.has_permission('{module}.{action}').
    The ViewSet must declare:  rbac_module = 'conges'

    Handles the 'self' pseudo-action for employee-only access to their own data.
    """

    def _module(self, view):
        return getattr(view, 'rbac_module', None)

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        module = self._module(view)
        if not module:
            return True

        action = METHOD_ACTION.get(request.method, 'view')

        if request.user.has_permission(f'{module}.{action}'):
            return True

        # Self-only: can list (GET) and submit (POST) their own records
        if request.user.has_permission(f'{module}.self'):
            return request.method in SAFE_METHODS or request.method == 'POST'

        return False

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False

        module = self._module(view)
        if not module:
            return True

        action = METHOD_ACTION.get(request.method, 'view')

        if request.user.has_permission(f'{module}.{action}'):
            return True

        if request.user.has_permission(f'{module}.self'):
            emp = _employe_of(request.user)
            if emp is None:
                return False
            obj_emp_pk = _employe_pk_of_obj(obj)
            if obj_emp_pk is not None:
                return obj_emp_pk == emp.pk
            # Direct User object (profil.self)
            if hasattr(obj, 'user_id'):
                return obj.user_id == request.user.pk
            if obj == request.user:
                return True

        return False
