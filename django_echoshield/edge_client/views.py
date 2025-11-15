"""
Views for the edge_client app.

Handles:
- Webhook endpoint for edge detection events
- Health check endpoint
- Node registry status endpoint
- Static file serving for browser-based detection UI
"""
import logging
import httpx
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils.decorators import method_decorator
import json

from .mappers import to_wirepacket, wirepacket_to_dict
from .node_registry import get_registry

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for edge client service.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'edge-client',
        'version': '1.0.0'
    })


@require_http_methods(["GET"])
def whoami(request):
    """
    Service identifier endpoint.
    """
    return JsonResponse({
        'service': 'edge-webapp-adapter',
        'version': '1.0.0',
        'description': 'EchoShield Edge Detection Webhook Handler'
    })


@method_decorator(csrf_exempt, name='dispatch')
class WebhookEdgeView(View):
    """
    Webhook endpoint for receiving edge detection events from browser clients.

    POST /webhook/edge
    Content-Type: application/json

    Payload:
    {
        "nodeId": "NODE_IPHONE_01",
        "time_ms": 1699999999999,
        "azimuth_deg": 45.0,
        "confidence": 0.87,
        "event": "drone",
        "lat": 52.5163,
        "lon": 13.3777,
        "acc_m": 15.0
    }
    """

    async def post(self, request):
        """Handle POST request with edge detection payload."""
        try:
            # Parse JSON payload
            payload = json.loads(request.body)
            logger.info(f"Received edge detection: node={payload.get('nodeId')}, "
                       f"confidence={payload.get('confidence')}")

            # Convert to WirePacket format
            wire_packet = to_wirepacket(payload)

            # Get ingest URL from settings
            ingest_url = settings.ECHOSHIELD.get(
                'INGEST_URL',
                'http://localhost:8000/api/v0/ingest/wire'
            )

            # Forward to Ingest API
            forwarded = False
            error_msg = None

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(ingest_url, json=wire_packet)
                    response.raise_for_status()
                    forwarded = True
                    logger.info(f"Forwarded event {wire_packet['event_id']} to ingest API")
            except httpx.HTTPError as e:
                error_msg = str(e)
                logger.error(f"Failed to forward to ingest API: {e}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Unexpected error forwarding to ingest API: {e}")

            # Return response
            return JsonResponse({
                'status': 'accepted' if forwarded else 'error',
                'event_id': wire_packet['event_id'],
                'forwarded': forwarded,
                'location_method': wire_packet['location_method'],
                'bearing_deg': wire_packet['bearing_deg'] / 100.0 if wire_packet.get('bearing_deg') else None,
                'gcc_phat': wire_packet.get('gcc_phat_metadata') is not None,
                'error': error_msg
            }, status=202 if forwarded else 500)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return JsonResponse({
                'status': 'error',
                'error': 'Invalid JSON payload'
            }, status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


@require_http_methods(["GET"])
def nodes_status(request):
    """
    Node registry status endpoint.

    Returns information about active nodes and recent detections.
    """
    registry = get_registry()
    status = registry.get_node_status()

    return JsonResponse({
        'status': 'ok',
        'registry': status
    })


@require_http_methods(["GET"])
def geo_test(request):
    """
    Simple GPS permission test page.

    Returns an HTML page that requests geolocation permission
    and displays the current coordinates.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GPS Test</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
            }
            .info {
                background: #f0f0f0;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            button {
                background: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <h1>GPS Permission Test</h1>
        <button onclick="getLocation()">Get Location</button>
        <div id="result" class="info"></div>
        <script>
            function getLocation() {
                const result = document.getElementById('result');
                if (!navigator.geolocation) {
                    result.innerHTML = 'Geolocation is not supported by your browser';
                    return;
                }

                result.innerHTML = 'Requesting location...';

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        result.innerHTML = `
                            <h3>Success!</h3>
                            <p><strong>Latitude:</strong> ${position.coords.latitude}</p>
                            <p><strong>Longitude:</strong> ${position.coords.longitude}</p>
                            <p><strong>Accuracy:</strong> ${position.coords.accuracy} meters</p>
                        `;
                    },
                    (error) => {
                        result.innerHTML = `
                            <h3>Error</h3>
                            <p>${error.message}</p>
                            <p>Make sure you're using HTTPS and have granted location permission.</p>
                        `;
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }
                );
            }
        </script>
    </body>
    </html>
    """
    return HttpResponse(html, content_type='text/html')
