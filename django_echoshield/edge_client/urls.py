"""
URL configuration for edge_client app.
"""
from django.urls import path
from django.views.generic import TemplateView
from . import views

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

    # Edge detection UI (index.html will be served from static files)
    path('', TemplateView.as_view(template_name='edge_client/index.html'), name='index'),
]
