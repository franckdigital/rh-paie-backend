from django.urls import path
from .views import DashboardGlobalView, DashboardRHView, DashboardPresenceView, DashboardPaieView, DashboardStatsView

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('global/', DashboardGlobalView.as_view(), name='dashboard-global'),
    path('rh/', DashboardRHView.as_view(), name='dashboard-rh'),
    path('presence/', DashboardPresenceView.as_view(), name='dashboard-presence'),
    path('paie/', DashboardPaieView.as_view(), name='dashboard-paie'),
]
