from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import PointageViewSet, AnomaliePointageViewSet, VerrouAppareilViewSet

router = DefaultRouter()
router.register('anomalies',         AnomaliePointageViewSet, basename='anomalies')
router.register('verrous-appareils', VerrouAppareilViewSet,   basename='verrous-appareils')
router.register('',                  PointageViewSet,         basename='pointages')
urlpatterns = [path('', include(router.urls))]
