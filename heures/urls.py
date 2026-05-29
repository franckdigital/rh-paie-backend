from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import ParametreHeuresViewSet, RecapHeuresViewSet

router = DefaultRouter()
router.register('parametres', ParametreHeuresViewSet, basename='parametres-heures')
router.register('recaps', RecapHeuresViewSet, basename='recaps-heures')
urlpatterns = [path('', include(router.urls))]
