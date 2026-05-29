from rest_framework import serializers
from .models import Notification, PushToken


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['id', 'titre', 'message', 'type', 'lu', 'url', 'created_at']
        read_only_fields = ['created_at']


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PushToken
        fields = ['id', 'token', 'platform', 'is_active', 'created_at']
