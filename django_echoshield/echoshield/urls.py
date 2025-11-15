"""
URL configuration for EchoShield project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Edge client app - webhook and node registry
    path('', include('edge_client.urls')),

    # Monitoring app - ingest API and dashboard
    path('api/', include('monitoring.urls')),
    
    # Dashboard alias for backward compatibility (redirect to /api/dashboard/)
    path('monitoring/dashboard/', RedirectView.as_view(url='/api/dashboard/', permanent=False), name='dashboard_redirect'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
