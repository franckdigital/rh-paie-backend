from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Role, RolePermission, MODULES_CHOICES, ACTIONS_CHOICES
from .serializers import RoleSerializer, RoleWriteSerializer
from users.permissions import RBACPermission


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related('permissions').all()
    rbac_module = 'roles'
    permission_classes = [permissions.IsAuthenticated, RBACPermission]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RoleWriteSerializer
        return RoleSerializer

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_systeme:
            return Response({'detail': 'Les rôles système ne peuvent pas être supprimés.'}, status=400)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def meta(self, request):
        return Response({
            'modules': [{'code': m[0], 'label': m[1]} for m in MODULES_CHOICES if m[0] != '*'],
            'actions': [{'code': a[0], 'label': a[1]} for a in ACTIONS_CHOICES],
        })

    @action(detail=True, methods=['post'])
    def sync_permissions(self, request, pk=None):
        role = self.get_object()
        if role.is_systeme:
            return Response({'detail': 'Rôle système : permissions non modifiables.'}, status=400)
        permissions_data = request.data.get('permissions', [])
        role.permissions.all().delete()
        for perm in permissions_data:
            module = perm.get('module')
            action_val = perm.get('action')
            if module and action_val:
                RolePermission.objects.get_or_create(role=role, module=module, action=action_val)
        return Response(RoleSerializer(role).data)

    @action(detail=True, methods=['get'])
    def utilisateurs(self, request, pk=None):
        from users.serializers import UserSerializer
        role = self.get_object()
        return Response(UserSerializer(role.utilisateurs.all(), many=True).data)

    @action(detail=True, methods=['post'])
    def assigner(self, request, pk=None):
        """Assigner ce rôle à un ou plusieurs utilisateurs."""
        role = self.get_object()
        user_ids = request.data.get('user_ids', [])
        from users.models import User
        updated = User.objects.filter(id__in=user_ids).update(role_obj=role)
        return Response({'updated': updated})
