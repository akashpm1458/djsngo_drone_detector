"""
URL configuration for edge_client app.
"""
from django.urls import path
from django.views.generic import TemplateView
from . import views, config_views, audio_views

app_name = 'edge_client'

urlpatterns = [
    # Health and service info
    path('health', views.health_check, name='health'),
    path('whoami', views.whoami, name='whoami'),

    # Webhook endpoint
    path('webhook/edge', views.WebhookEdgeView.as_view(), name='webhook_edge'),

    # Node registry status
    path('nodes/status', views.nodes_status, name='nodes_status'),

    # GPS test page
    path('geo-test', views.geo_test, name='geo_test'),

    # Audio processing API
    path('api/audio/upload', audio_views.AudioUploadView.as_view(), name='audio_upload'),
    path('api/audio/task/<str:task_id>', audio_views.task_status, name='task_status'),

    # Detection configuration API
    path('api/detection-config/list', config_views.list_configs, name='config_list'),
    path('api/detection-config/active', config_views.get_active_config, name='config_active'),
    path('api/detection-config/create', config_views.ConfigCreateView.as_view(), name='config_create'),
    path('api/detection-config/<int:config_id>', config_views.get_config_detail, name='config_detail'),
    path('api/detection-config/<int:config_id>/update', config_views.ConfigUpdateView.as_view(), name='config_update'),
    path('api/detection-config/<int:config_id>/activate', config_views.activate_config, name='config_activate'),
    path('api/detection-config/<int:config_id>/delete', config_views.delete_config, name='config_delete'),

    # Web interface
    path('detect', TemplateView.as_view(template_name='edge_client/detect.html'), name='detect'),

    # Edge detection UI (index.html will be served from static files)
    path('', TemplateView.as_view(template_name='edge_client/index.html'), name='index'),
]
