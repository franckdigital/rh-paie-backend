from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, PushTokenViewSet

router = DefaultRouter()
router.register('push-tokens', PushTokenViewSet, basename='push-token')
router.register('',            NotificationViewSet, basename='notification')

urlpatterns = router.urls
