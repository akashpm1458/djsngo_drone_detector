"""
Configuration management views for edge detection.

Provides REST API endpoints for managing detection configurations.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils.decorators import method_decorator
import json

from core.models import DetectionConfig

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def list_configs(request):
    """
    List all detection configurations.

    GET /api/detection-config/list
    """
    configs = DetectionConfig.objects.all()

    config_list = []
    for config in configs:
        config_list.append({
            'id': config.id,
            'config_name': config.config_name,
            'method': config.method,
            'method_display': config.get_method_display(),
            'is_active': config.is_active,
            'fundamental_freq_hz': config.fundamental_freq_hz,
            'n_harmonics': config.n_harmonics,
            'confidence_threshold': config.confidence_threshold,
            'created_at': config.created_at.isoformat() if config.created_at else None,
        })

    return JsonResponse({
        'status': 'ok',
        'configs': config_list
    })


@require_http_methods(["GET"])
def get_active_config(request):
    """
    Get the currently active detection configuration.

    GET /api/detection-config/active
    """
    try:
        config = DetectionConfig.objects.get(is_active=True)

        return JsonResponse({
            'status': 'ok',
            'config': _config_to_dict(config)
        })
    except DetectionConfig.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': 'No active configuration found'
        }, status=404)


@require_http_methods(["GET"])
def get_config_detail(request, config_id):
    """
    Get detailed configuration by ID.

    GET /api/detection-config/{config_id}
    """
    try:
        config = DetectionConfig.objects.get(id=config_id)

        return JsonResponse({
            'status': 'ok',
            'config': _config_to_dict(config)
        })
    except DetectionConfig.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': f'Configuration {config_id} not found'
        }, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class ConfigCreateView(View):
    """
    Create a new detection configuration.

    POST /api/detection-config/create
    """

    def post(self, request):
        try:
            data = json.loads(request.body)

            # Validate required fields
            if 'config_name' not in data:
                return JsonResponse({
                    'status': 'error',
                    'error': 'config_name is required'
                }, status=400)

            # Create configuration
            config = DetectionConfig.objects.create(
                config_name=data['config_name'],
                method=data.get('method', 'combined'),
                is_active=data.get('is_active', False),
                fundamental_freq_hz=data.get('fundamental_freq_hz', 150.0),
                n_harmonics=data.get('n_harmonics', 7),
                confidence_threshold=data.get('confidence_threshold', 0.75),
                freq_band_low_hz=data.get('freq_band_low_hz', 100.0),
                freq_band_high_hz=data.get('freq_band_high_hz', 5000.0),
                harmonic_bandwidth_hz=data.get('harmonic_bandwidth_hz', 40.0),
                snr_min_db=data.get('snr_min_db', 0.0),
                snr_max_db=data.get('snr_max_db', 30.0),
                harmonic_min_snr_db=data.get('harmonic_min_snr_db', 3.0),
                temporal_window=data.get('temporal_window', 5),
                weight_snr=data.get('weight_snr', 0.4),
                weight_harmonic=data.get('weight_harmonic', 0.3),
                weight_temporal=data.get('weight_temporal', 0.3),
                mic_spacing_m=data.get('mic_spacing_m', 0.14),
                frame_length_ms=data.get('frame_length_ms', 64.0),
                hop_length_ms=data.get('hop_length_ms', 32.0),
                created_by=data.get('created_by')
            )

            logger.info(f"Created configuration: {config.config_name} (ID: {config.id})")

            return JsonResponse({
                'status': 'created',
                'config': _config_to_dict(config)
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating configuration: {e}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ConfigUpdateView(View):
    """
    Update an existing detection configuration.

    PUT /api/detection-config/{config_id}/update
    """

    def put(self, request, config_id):
        try:
            config = DetectionConfig.objects.get(id=config_id)
            data = json.loads(request.body)

            # Update fields
            if 'config_name' in data:
                config.config_name = data['config_name']
            if 'method' in data:
                config.method = data['method']
            if 'is_active' in data:
                config.is_active = data['is_active']
            if 'fundamental_freq_hz' in data:
                config.fundamental_freq_hz = data['fundamental_freq_hz']
            if 'n_harmonics' in data:
                config.n_harmonics = data['n_harmonics']
            if 'confidence_threshold' in data:
                config.confidence_threshold = data['confidence_threshold']
            if 'freq_band_low_hz' in data:
                config.freq_band_low_hz = data['freq_band_low_hz']
            if 'freq_band_high_hz' in data:
                config.freq_band_high_hz = data['freq_band_high_hz']
            if 'harmonic_bandwidth_hz' in data:
                config.harmonic_bandwidth_hz = data['harmonic_bandwidth_hz']
            if 'snr_min_db' in data:
                config.snr_min_db = data['snr_min_db']
            if 'snr_max_db' in data:
                config.snr_max_db = data['snr_max_db']
            if 'harmonic_min_snr_db' in data:
                config.harmonic_min_snr_db = data['harmonic_min_snr_db']
            if 'temporal_window' in data:
                config.temporal_window = data['temporal_window']
            if 'weight_snr' in data:
                config.weight_snr = data['weight_snr']
            if 'weight_harmonic' in data:
                config.weight_harmonic = data['weight_harmonic']
            if 'weight_temporal' in data:
                config.weight_temporal = data['weight_temporal']
            if 'mic_spacing_m' in data:
                config.mic_spacing_m = data['mic_spacing_m']
            if 'frame_length_ms' in data:
                config.frame_length_ms = data['frame_length_ms']
            if 'hop_length_ms' in data:
                config.hop_length_ms = data['hop_length_ms']

            config.save()

            logger.info(f"Updated configuration: {config.config_name} (ID: {config.id})")

            return JsonResponse({
                'status': 'updated',
                'config': _config_to_dict(config)
            })

        except DetectionConfig.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': f'Configuration {config_id} not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating configuration: {e}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def activate_config(request, config_id):
    """
    Activate a specific configuration.

    POST /api/detection-config/{config_id}/activate
    """
    try:
        config = DetectionConfig.objects.get(id=config_id)
        config.is_active = True
        config.save()  # This will automatically deactivate others

        logger.info(f"Activated configuration: {config.config_name} (ID: {config.id})")

        return JsonResponse({
            'status': 'activated',
            'config': _config_to_dict(config)
        })

    except DetectionConfig.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': f'Configuration {config_id} not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error activating configuration: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_config(request, config_id):
    """
    Delete a configuration.

    DELETE /api/detection-config/{config_id}
    """
    try:
        config = DetectionConfig.objects.get(id=config_id)

        if config.is_active:
            return JsonResponse({
                'status': 'error',
                'error': 'Cannot delete active configuration'
            }, status=400)

        config_name = config.config_name
        config.delete()

        logger.info(f"Deleted configuration: {config_name} (ID: {config_id})")

        return JsonResponse({
            'status': 'deleted',
            'config_id': config_id
        })

    except DetectionConfig.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'error': f'Configuration {config_id} not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


def _config_to_dict(config: DetectionConfig) -> dict:
    """Convert DetectionConfig model to dictionary."""
    return {
        'id': config.id,
        'config_name': config.config_name,
        'method': config.method,
        'method_display': config.get_method_display(),
        'is_active': config.is_active,
        'fundamental_freq_hz': config.fundamental_freq_hz,
        'n_harmonics': config.n_harmonics,
        'confidence_threshold': config.confidence_threshold,
        'freq_band_low_hz': config.freq_band_low_hz,
        'freq_band_high_hz': config.freq_band_high_hz,
        'harmonic_bandwidth_hz': config.harmonic_bandwidth_hz,
        'snr_min_db': config.snr_min_db,
        'snr_max_db': config.snr_max_db,
        'harmonic_min_snr_db': config.harmonic_min_snr_db,
        'temporal_window': config.temporal_window,
        'weight_snr': config.weight_snr,
        'weight_harmonic': config.weight_harmonic,
        'weight_temporal': config.weight_temporal,
        'mic_spacing_m': config.mic_spacing_m,
        'frame_length_ms': config.frame_length_ms,
        'hop_length_ms': config.hop_length_ms,
        'created_at': config.created_at.isoformat() if config.created_at else None,
        'updated_at': config.updated_at.isoformat() if config.updated_at else None,
        'created_by': config.created_by,
    }
