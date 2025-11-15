"""
Views for the monitoring app.

Handles:
- Ingest API endpoint for WirePacket ingestion
- Dashboard views for monitoring UI
- Event and Track API endpoints
"""
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils.decorators import method_decorator
from django.db.models import Count, Avg, Max, Min, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import json

from core.models import Event, Track, TrackContributor
from .serializers import (
    WirePacketSerializer, EventSerializer, TrackSerializer,
    CanonicalEventSerializer
)
from .wire_codec import to_canonical, get_current_time_ns

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for monitoring service."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'monitoring',
        'version': '1.0.0'
    })


@method_decorator(csrf_exempt, name='dispatch')
class IngestWireView(View):
    """
    Ingest API endpoint for receiving WirePacket events.

    POST /api/v0/ingest/wire
    Content-Type: application/json

    Accepts WirePacket format and converts to Canonical Event.
    """

    def post(self, request):
        """Handle POST request with WirePacket payload."""
        try:
            # Parse JSON payload
            wire_packet = json.loads(request.body)
            logger.info(f"Received WirePacket: event_id={wire_packet.get('event_id')}, "
                       f"node={wire_packet.get('sensor_node_id')}")

            # Validate with serializer
            serializer = WirePacketSerializer(data=wire_packet)
            if not serializer.is_valid():
                logger.error(f"Invalid WirePacket: {serializer.errors}")
                return JsonResponse({
                    'status': 'error',
                    'errors': serializer.errors
                }, status=400)

            # Get server receipt timestamp
            rx_ns = get_current_time_ns()

            # Convert to Canonical Event
            canonical = to_canonical(serializer.validated_data, rx_ns)

            # Create Event model instance
            event = Event.objects.create(
                event_id=canonical['event_id'],
                sensor_type=canonical['sensor_type'],
                sensor_node_id=canonical['sensor_node_id'],
                ts_ns=canonical['ts_ns'],
                rx_ns=canonical['rx_ns'],
                latency_ns=canonical['latency_ns'],
                latency_status=canonical['latency_status'],
                lat=canonical.get('lat'),
                lon=canonical.get('lon'),
                error_radius_m=canonical.get('error_radius_m'),
                bearing_deg=canonical.get('bearing_deg'),
                bearing_conf=canonical.get('bearing_conf'),
                n_objects=canonical.get('n_objects'),
                event_code=canonical.get('event_code'),
                location_method=canonical.get('location_method'),
                packet_version=canonical.get('packet_version'),
                validity_status=canonical['validity_status'],
                duplicate_flag=canonical['duplicate_flag'],
                gcc_phat_metadata=canonical.get('gcc_phat_metadata'),
                raw_wire_json=canonical['raw_wire_json']
            )

            logger.info(f"Event created: {event.event_id}, latency={event.latency_ms:.2f}ms, "
                       f"status={event.latency_status}")

            # Return response
            return JsonResponse({
                'status': 'accepted',
                'event_id': event.event_id,
                'location_method': event.location_method,
                'bearing_deg': event.bearing_deg,
                'latency_ms': event.latency_ms,
                'latency_status': event.latency_status,
                'gcc_phat': event.gcc_phat_metadata is not None
            }, status=202)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return JsonResponse({
                'status': 'error',
                'error': 'Invalid JSON payload'
            }, status=400)
        except Exception as e:
            logger.error(f"Error processing ingest: {e}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for Event model.

    Provides list and retrieve endpoints for events.
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    ordering = ['-rx_ns']
    filterset_fields = [
        'sensor_type', 'sensor_node_id', 'latency_status',
        'validity_status', 'duplicate_flag', 'location_method'
    ]
    search_fields = ['event_id', 'sensor_node_id', 'object_track_id']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get event statistics.

        Returns:
            - total_events
            - active_nodes
            - latency_percentiles (p50, p95, p99)
            - events_by_status
        """
        # Total events
        total_events = Event.objects.count()

        # Active nodes (nodes with events in last 5 minutes)
        five_minutes_ago_ns = get_current_time_ns() - (5 * 60 * 1_000_000_000)
        active_nodes = Event.objects.filter(
            rx_ns__gte=five_minutes_ago_ns
        ).values('sensor_node_id').distinct().count()

        # Events by status
        events_by_status = {
            'normal': Event.objects.filter(latency_status='normal').count(),
            'delayed': Event.objects.filter(latency_status='delayed').count(),
            'obsolete': Event.objects.filter(latency_status='obsolete').count(),
        }

        # Validity status
        events_by_validity = {
            'valid': Event.objects.filter(validity_status='valid').count(),
            'invalid': Event.objects.filter(validity_status='invalid').count(),
            'unknown': Event.objects.filter(validity_status='unknown').count(),
        }

        # Duplicates
        duplicate_count = Event.objects.filter(duplicate_flag=True).count()

        return Response({
            'total_events': total_events,
            'active_nodes': active_nodes,
            'events_by_latency_status': events_by_status,
            'events_by_validity': events_by_validity,
            'duplicate_count': duplicate_count
        })


class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for Track model.

    Provides list and retrieve endpoints for tracks.
    """
    queryset = Track.objects.prefetch_related('contributors')
    serializer_class = TrackSerializer
    ordering = ['-last_ts_ns']
    filterset_fields = ['method', 'status']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active tracks."""
        active_tracks = self.queryset.filter(status='active')
        serializer = self.get_serializer(active_tracks, many=True)
        return Response(serializer.data)


def dashboard_view(request):
    """
    Main monitoring dashboard view.

    Displays:
    - KPI metrics (total events, active nodes, latency stats)
    - Recent events table
    - Interactive map with bearing corridors
    - Latency analytics
    """
    # Get recent events (last 1000)
    recent_events = Event.objects.select_related().order_by('-rx_ns')[:1000]

    # Calculate KPIs
    total_events = Event.objects.count()

    # Active nodes (last 5 minutes)
    five_minutes_ago_ns = get_current_time_ns() - (5 * 60 * 1_000_000_000)
    active_nodes = Event.objects.filter(
        rx_ns__gte=five_minutes_ago_ns
    ).values('sensor_node_id').distinct().count()

    # Latency statistics (convert ns to ms)
    latency_stats = Event.objects.aggregate(
        avg_latency=Avg('latency_ns'),
        min_latency=Min('latency_ns'),
        max_latency=Max('latency_ns')
    )

    # Convert to milliseconds
    avg_latency_ms = (latency_stats['avg_latency'] or 0) / 1_000_000
    min_latency_ms = (latency_stats['min_latency'] or 0) / 1_000_000
    max_latency_ms = (latency_stats['max_latency'] or 0) / 1_000_000

    # Active tracks
    active_tracks = Track.objects.filter(status='active').count()

    context = {
        'total_events': total_events,
        'active_nodes': active_nodes,
        'avg_latency_ms': avg_latency_ms,
        'min_latency_ms': min_latency_ms,
        'max_latency_ms': max_latency_ms,
        'active_tracks': active_tracks,
        'recent_events': recent_events[:50],  # Display top 50
    }

    return render(request, 'monitoring/dashboard.html', context)


def events_api(request):
    """
    JSON API endpoint for fetching events data.

    Used by dashboard for real-time updates.
    """
    # Get filter parameters
    limit = int(request.GET.get('limit', 100))
    offset = int(request.GET.get('offset', 0))
    node_id = request.GET.get('node_id')
    latency_status = request.GET.get('latency_status')

    # Build query
    queryset = Event.objects.all()

    if node_id:
        queryset = queryset.filter(sensor_node_id=node_id)

    if latency_status:
        queryset = queryset.filter(latency_status=latency_status)

    # Get total count
    total_count = queryset.count()

    # Get events with pagination
    events = queryset.order_by('-rx_ns')[offset:offset + limit]

    # Serialize to JSON
    events_data = []
    for event in events:
        events_data.append({
            'event_id': event.event_id,
            'sensor_type': event.sensor_type,
            'sensor_node_id': event.sensor_node_id,
            'ts_ns': event.ts_ns,
            'rx_ns': event.rx_ns,
            'latency_ms': event.latency_ms,
            'latency_status': event.latency_status,
            'lat': event.lat,
            'lon': event.lon,
            'bearing_deg': event.bearing_deg,
            'bearing_conf': event.bearing_conf,
            'duplicate_flag': event.duplicate_flag,
            'object_track_id': event.object_track_id,
            'created_at': event.created_at.isoformat() if event.created_at else None
        })

    return JsonResponse({
        'total_count': total_count,
        'events': events_data,
        'limit': limit,
        'offset': offset
    })
