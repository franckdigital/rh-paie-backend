from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import SiteViewSet, UniteViewSet

router = DefaultRouter()
router.register('unites', UniteViewSet, basename='unites')
router.register('', SiteViewSet, basename='sites')
urlpatterns = [path('', include(router.urls))]
