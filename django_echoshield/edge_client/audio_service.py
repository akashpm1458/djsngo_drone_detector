"""
Audio processing service for drone detection.

Handles audio file uploads, processing, and detection result storage.
"""
import logging
import numpy as np
import tempfile
import os
from typing import Dict, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class AudioService:
    """Service for processing audio files for drone detection."""

    SUPPORTED_FORMATS = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    MAX_FILE_SIZE_MB = 50
    MAX_DURATION_SEC = 300  # 5 minutes

    def __init__(self):
        """Initialize audio service."""
        self.logger = logger

    def validate_audio_file(self, audio_file: UploadedFile) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded audio file.

        Parameters
        ----------
        audio_file : UploadedFile
            Django uploaded file object

        Returns
        -------
        is_valid : bool
            Whether the file is valid
        error_message : str or None
            Error message if invalid
        """
        # Check file extension
        file_ext = os.path.splitext(audio_file.name)[1].lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported format {file_ext}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"

        # Check file size
        file_size_mb = audio_file.size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            return False, f"File too large ({file_size_mb:.1f} MB). Max: {self.MAX_FILE_SIZE_MB} MB"

        return True, None

    def load_audio_file(self, audio_file: UploadedFile) -> Tuple[np.ndarray, int, bool]:
        """
        Load audio file into numpy array.

        Parameters
        ----------
        audio_file : UploadedFile
            Django uploaded file object

        Returns
        -------
        audio : np.ndarray
            Audio signal array
        fs : int
            Sampling rate
        is_stereo : bool
            Whether audio is stereo

        Raises
        ------
        ValueError
            If audio file cannot be loaded
        """
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp_file:
            for chunk in audio_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            # Load audio using scipy or soundfile
            audio, fs, is_stereo = self._load_audio_from_path(tmp_path)

            # Check duration
            duration = len(audio) / fs if not is_stereo else audio.shape[0] / fs
            if duration > self.MAX_DURATION_SEC:
                raise ValueError(
                    f"Audio too long ({duration:.1f}s). Max: {self.MAX_DURATION_SEC}s"
                )

            self.logger.info(f"Loaded audio: {audio_file.name}, "
                           f"fs={fs} Hz, stereo={is_stereo}, duration={duration:.2f}s")

            return audio, fs, is_stereo

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _load_audio_from_path(self, file_path: str) -> Tuple[np.ndarray, int, bool]:
        """
        Load audio from file path.

        Parameters
        ----------
        file_path : str
            Path to audio file

        Returns
        -------
        audio : np.ndarray
            Audio signal
        fs : int
            Sampling rate
        is_stereo : bool
            Whether stereo
        """
        # Try scipy first
        try:
            import scipy.io.wavfile as wavfile
            fs, audio = wavfile.read(file_path)

            # Convert to float
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            elif audio.dtype == np.uint8:
                audio = (audio.astype(np.float32) - 128) / 128.0

            is_stereo = (audio.ndim > 1)

            if is_stereo and audio.shape[0] < audio.shape[1]:
                audio = audio.T

            return audio, fs, is_stereo

        except Exception as e:
            self.logger.warning(f"scipy failed, trying soundfile: {e}")

        # Try soundfile
        try:
            import soundfile as sf
            audio, fs = sf.read(file_path)

            is_stereo = (audio.ndim > 1)

            if is_stereo and audio.shape[0] < audio.shape[1]:
                audio = audio.T

            return audio, int(fs), is_stereo

        except ImportError:
            raise ValueError("Neither scipy nor soundfile available for audio loading")
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")

    def process_audio_with_config(
        self,
        audio: np.ndarray,
        fs: int,
        is_stereo: bool,
        config: Dict
    ) -> Dict:
        """
        Process audio with detection configuration.

        Parameters
        ----------
        audio : np.ndarray
            Audio signal
        fs : int
            Sampling rate
        is_stereo : bool
            Whether stereo
        config : dict
            Detection configuration

        Returns
        -------
        result : dict
            Detection result
        """
        from .detection_processor import DetectionProcessor

        # Create processor
        processor = DetectionProcessor(config)

        # Process audio
        result = processor.process_audio(audio, fs, is_stereo)

        return result.to_dict()

    def create_event_from_result(
        self,
        result: Dict,
        sensor_node_id: str,
        file_name: str,
        config_id: int
    ) -> 'Event':
        """
        Create Event model instance from detection result.

        Parameters
        ----------
        result : dict
            Detection result from processor
        sensor_node_id : str
            Node identifier
        file_name : str
            Original file name
        config_id : int
            Configuration ID used

        Returns
        -------
        event : Event
            Created event instance
        """
        from core.models import Event
        from monitoring.wire_codec import get_current_time_ns
        import uuid

        ts_ns = get_current_time_ns()
        rx_ns = ts_ns  # Same for uploaded files

        event = Event.objects.create(
            event_id=str(uuid.uuid4()),
            sensor_type=Event.SENSOR_ACOUSTIC,
            sensor_node_id=sensor_node_id,
            ts_ns=ts_ns,
            rx_ns=rx_ns,
            latency_ns=0,
            latency_status=Event.LATENCY_NORMAL,

            # Detection results
            detection_method=result.get('detection_method'),
            detection_confidence=result.get('confidence'),
            snr_db=result.get('snr_db'),
            harmonic_score=result.get('harmonic_score'),
            temporal_score=result.get('temporal_score'),
            doa_angle_deg=result.get('doa_angle_deg'),

            # Bearing (use DOA if available)
            bearing_deg=result.get('doa_angle_deg'),
            bearing_conf=result.get('confidence'),
            bearing_std_deg=result.get('doa_std_deg'),

            # Metadata
            n_objects=1 if result.get('detected') else 0,
            event_code='drone' if result.get('detected') else 'no_detection',
            location_method=Event.LOC_BEARING_ONLY,
            validity_status=Event.VALIDITY_VALID,
            duplicate_flag=False,

            # Raw data
            raw_wire_json={
                'file_name': file_name,
                'config_id': config_id,
                'processing_time_sec': result.get('processing_time_sec'),
                'n_frames': result.get('n_frames'),
                'result': result
            }
        )

        self.logger.info(f"Created event {event.event_id} from file {file_name}: "
                        f"detected={result.get('detected')}, confidence={result.get('confidence'):.3f}")

        return event


# Global service instance
audio_service = AudioService()
