from rest_framework import serializers
from .models import Role, RolePermission, MODULES_CHOICES, ACTIONS_CHOICES


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RolePermission
        fields = ['id', 'module', 'action']


class RoleSerializer(serializers.ModelSerializer):
    permissions  = RolePermissionSerializer(many=True, read_only=True)
    users_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Role
        fields = [
            'id', 'code', 'label', 'description', 'couleur',
            'is_systeme', 'created_at', 'permissions', 'users_count',
        ]
        read_only_fields = ['created_at', 'is_systeme']

    def get_users_count(self, obj):
        return obj.utilisateurs.count()


class RoleWriteSerializer(serializers.ModelSerializer):
    permissions = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model  = Role
        fields = ['code', 'label', 'description', 'couleur', 'permissions']

    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        self._sync_permissions(role, permissions_data)
        return role

    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if permissions_data is not None:
            self._sync_permissions(instance, permissions_data)
        return instance

    def _sync_permissions(self, role, permissions_data):
        role.permissions.all().delete()
        for perm in permissions_data:
            module = perm.get('module')
            action = perm.get('action')
            if module and action:
                RolePermission.objects.get_or_create(role=role, module=module, action=action)
