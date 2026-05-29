from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import BulletinPaieViewSet, ElementSalaireViewSet, JournalPaieViewSet

router = DefaultRouter()
router.register('bulletins', BulletinPaieViewSet, basename='bulletins')
router.register('elements', ElementSalaireViewSet, basename='elements')
router.register('journaux', JournalPaieViewSet, basename='journaux-paie')
urlpatterns = [path('', include(router.urls))]
