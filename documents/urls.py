from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import DocumentViewSet, CategorieDocumentViewSet

router = DefaultRouter()
# Specific prefixes BEFORE the empty-prefix viewset to avoid catch-all collision
router.register('categories', CategorieDocumentViewSet, basename='categories-docs')
router.register('', DocumentViewSet, basename='documents')
urlpatterns = [path('', include(router.urls))]
