from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, UserListCreateView, UserDetailView,
    MeView, LogoutView, ChangePasswordView,
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/', UserListCreateView.as_view(), name='users-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='users-detail'),
    path('me/', MeView.as_view(), name='me'),
]
