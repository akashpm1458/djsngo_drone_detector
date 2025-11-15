"""
URL configuration for monitoring app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'monitoring'

# REST API router
router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'tracks', views.TrackViewSet, basename='track')

urlpatterns = [
    # Health check
    path('health', views.health_check, name='health'),

    # Ingest API endpoint
    path('v0/ingest/wire', views.IngestWireView.as_view(), name='ingest_wire'),

    # REST API endpoints
    path('v0/', include(router.urls)),

    # Dashboard views
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/events/', views.events_api, name='events_api'),
    
    # Dashboard API endpoints (for backward compatibility)
    path('v0/events/stats/', views.EventViewSet.as_view({'get': 'stats'}), name='events_stats'),
]
