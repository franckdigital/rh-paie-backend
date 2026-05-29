from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import PresenceViewSet, JourFerieViewSet, RapportPresenceViewSet

router = DefaultRouter()
router.register('jours-feries', JourFerieViewSet, basename='jours-feries')
router.register('rapports', RapportPresenceViewSet, basename='rapports-presence')
router.register('', PresenceViewSet, basename='presences')
urlpatterns = [path('', include(router.urls))]
