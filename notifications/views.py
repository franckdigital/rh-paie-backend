from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, PushToken
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def non_lues(self, request):
        qs = self.get_queryset().filter(lu=False)
        return Response({
            'count': qs.count(),
            'notifications': NotificationSerializer(qs[:20], many=True).data,
        })

    @action(detail=True, methods=['post'])
    def marquer_lu(self, request, pk=None):
        notif = self.get_object()
        notif.lu = True
        notif.save(update_fields=['lu'])
        return Response({'status': 'lu'})

    @action(detail=False, methods=['post'])
    def tout_marquer_lu(self, request):
        self.get_queryset().filter(lu=False).update(lu=True)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['delete'])
    def vider(self, request):
        self.get_queryset().filter(lu=True).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushTokenViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def enregistrer(self, request):
        token    = request.data.get('token')
        platform = request.data.get('platform', 'expo')
        if not token:
            return Response({'detail': 'token requis'}, status=400)
        PushToken.objects.update_or_create(
            user=request.user, token=token,
            defaults={'platform': platform, 'is_active': True},
        )
        return Response({'status': 'registered'})

    @action(detail=False, methods=['post'])
    def supprimer(self, request):
        token = request.data.get('token')
        if token:
            PushToken.objects.filter(user=request.user, token=token).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
