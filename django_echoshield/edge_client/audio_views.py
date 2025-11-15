"""
Audio processing views for file upload and real-time detection.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils.decorators import method_decorator
from core.models import DetectionConfig
from .audio_service import audio_service

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AudioUploadView(View):
    """
    Handle audio file uploads for drone detection.

    POST /edge_client/api/audio/upload
    Content-Type: multipart/form-data

    Form data:
        - audio_file: Audio file to process
        - sensor_node_id: (optional) Node identifier
        - use_async: (optional) Process asynchronously via Celery
    """

    def post(self, request):
        try:
            # Get uploaded file
            if 'audio_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No audio file provided'
                }, status=400)

            audio_file = request.FILES['audio_file']
            sensor_node_id = request.POST.get('sensor_node_id', 'web_upload')
            use_async = request.POST.get('use_async', 'false').lower() == 'true'
            use_ml_model = request.POST.get('use_ml_model', 'false').lower() == 'true'

            logger.info(f"Received audio upload: {audio_file.name}, "
                       f"size={audio_file.size} bytes, async={use_async}")

            # Validate file
            is_valid, error_msg = audio_service.validate_audio_file(audio_file)
            if not is_valid:
                return JsonResponse({
                    'status': 'error',
                    'error': error_msg
                }, status=400)

            # Get active configuration
            try:
                config = DetectionConfig.objects.get(is_active=True)
            except DetectionConfig.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'error': 'No active detection configuration found'
                }, status=500)

            # Process asynchronously if requested
            if use_async:
                from .tasks import process_audio_task

                # Save file temporarily and queue task
                task = process_audio_task.delay(
                    audio_file.read(),
                    audio_file.name,
                    sensor_node_id,
                    config.id
                )

                return JsonResponse({
                    'status': 'processing',
                    'task_id': task.id,
                    'message': 'Audio queued for processing'
                }, status=202)

            # Process synchronously
            try:
                # Load audio
                audio, fs, is_stereo = audio_service.load_audio_file(audio_file)

                # Get config dict
                config_dict = self._config_to_dict(config)
                
                # Override ML model setting if requested
                if use_ml_model:
                    config_dict['use_ml_model'] = True
                    config_dict['method'] = 'ml_model'

                # Process audio
                result = audio_service.process_audio_with_config(
                    audio, fs, is_stereo, config_dict
                )

                # Create event
                event = audio_service.create_event_from_result(
                    result, sensor_node_id, audio_file.name, config.id
                )

                return JsonResponse({
                    'status': 'success',
                    'event_id': event.event_id,
                    'result': {
                        'detected': result['detected'],
                        'confidence': result['confidence'],
                        'detection_method': result['detection_method'],
                        'snr_db': result['snr_db'],
                        'doa_angle_deg': result['doa_angle_deg'],
                        'processing_time_sec': result['processing_time_sec']
                    }
                }, status=200)

            except Exception as e:
                logger.error(f"Error processing audio: {e}", exc_info=True)
                return JsonResponse({
                    'status': 'error',
                    'error': f'Processing failed: {str(e)}'
                }, status=500)

        except Exception as e:
            logger.error(f"Error in audio upload: {e}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)

    def _config_to_dict(self, config: DetectionConfig) -> dict:
        """Convert DetectionConfig to dict for processor."""
        return {
            'method': config.method,
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
            'use_ml_model': config.use_ml_model,
            'ml_model_path': config.ml_model_path,
        }


@require_http_methods(["GET"])
def task_status(request, task_id):
    """
    Get status of async processing task.

    GET /edge_client/api/audio/task/<task_id>
    """
    try:
        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        if task.ready():
            if task.successful():
                result = task.result
                return JsonResponse({
                    'status': 'completed',
                    'task_id': task_id,
                    'result': result
                })
            else:
                return JsonResponse({
                    'status': 'failed',
                    'task_id': task_id,
                    'error': str(task.info)
                }, status=500)
        else:
            return JsonResponse({
                'status': 'processing',
                'task_id': task_id,
                'state': task.state
            })

    except Exception as e:
        logger.error(f"Error checking task status: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
