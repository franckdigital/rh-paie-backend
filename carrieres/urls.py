from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import EvenementCarriereViewSet, RegleEvolutionCarriereViewSet

router = DefaultRouter()
router.register('evenements', EvenementCarriereViewSet, basename='evenements-carriere')
router.register('regles', RegleEvolutionCarriereViewSet, basename='regles-carriere')
urlpatterns = [path('', include(router.urls))]
