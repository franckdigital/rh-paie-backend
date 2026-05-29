from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class UserSerializer(serializers.ModelSerializer):
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    site_nom       = serializers.CharField(source='site.nom', read_only=True)
    role_display   = serializers.CharField(source='get_role_display', read_only=True)
    role_label     = serializers.CharField(read_only=True)
    role_obj_label = serializers.CharField(source='role_obj.label', read_only=True, allow_null=True)
    role_obj_couleur = serializers.CharField(source='role_obj.couleur', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'role_label', 'role_obj', 'role_obj_label', 'role_obj_couleur',
            'telephone', 'photo',
            'entreprise', 'entreprise_nom', 'site', 'site_nom',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ChangePasswordSerializer(serializers.Serializer):
    ancien_mot_de_passe = serializers.CharField(required=True)
    nouveau_mot_de_passe = serializers.CharField(required=True, min_length=8)
    confirmation = serializers.CharField(required=True)

    def validate(self, data):
        if data['nouveau_mot_de_passe'] != data['confirmation']:
            raise serializers.ValidationError({'confirmation': 'Les mots de passe ne correspondent pas.'})
        return data


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'telephone']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['role_obj_id'] = user.role_obj_id
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
