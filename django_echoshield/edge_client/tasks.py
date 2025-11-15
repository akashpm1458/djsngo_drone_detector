"""
Celery tasks for asynchronous audio processing.
"""
import logging
import numpy as np
import tempfile
import os
from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_audio_task(self, audio_bytes, file_name, sensor_node_id, config_id):
    """
    Process audio file asynchronously.

    Parameters
    ----------
    audio_bytes : bytes
        Audio file content
    file_name : str
        Original file name
    sensor_node_id : str
        Node identifier
    config_id : int
        Configuration ID to use

    Returns
    -------
    result : dict
        Processing result with event_id
    """
    try:
        from core.models import DetectionConfig
        from .audio_service import audio_service

        logger.info(f"Processing audio task: {file_name}, config={config_id}")

        # Get configuration
        try:
            config = DetectionConfig.objects.get(id=config_id)
        except DetectionConfig.DoesNotExist:
            raise ValueError(f"Configuration {config_id} not found")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            # Load audio
            audio, fs, is_stereo = audio_service._load_audio_from_path(tmp_path)

            # Create config dict
            config_dict = {
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
            }

            # Process audio
            result = audio_service.process_audio_with_config(
                audio, fs, is_stereo, config_dict
            )

            # Create event
            event = audio_service.create_event_from_result(
                result, sensor_node_id, file_name, config_id
            )

            logger.info(f"Audio processing complete: {file_name}, event={event.event_id}")

            return {
                'event_id': event.event_id,
                'detected': result['detected'],
                'confidence': result['confidence'],
                'detection_method': result['detection_method'],
                'snr_db': result['snr_db'],
                'doa_angle_deg': result['doa_angle_deg'],
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as exc:
        logger.error(f"Error processing audio task: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)
