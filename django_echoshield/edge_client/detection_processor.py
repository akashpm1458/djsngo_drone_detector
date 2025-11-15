"""
Detection processor for acoustic drone detection.

Integrates signal processing modules and provides a unified API for
processing audio with configurable detection methods.
"""
import logging
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Import signal processing modules
from .energy_likelihood_detector import EnergyLikelihoodDetector
from .gcc_phat_doa import estimate_doa_gcc_phat, tdoa_to_doa_linear
from .framing_windowing import frame_and_window
from .fft import compute_fft_per_frame
from .harmonic_filter import frequency_harmonic_filter, make_harmonic_mask

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Results from audio processing and detection."""
    detected: bool
    confidence: float
    detection_method: str

    # Detection metrics
    snr_db: Optional[float] = None
    harmonic_score: Optional[float] = None
    temporal_score: Optional[float] = None

    # Direction of Arrival
    doa_angle_deg: Optional[float] = None
    doa_std_deg: Optional[float] = None

    # Additional metadata
    mean_doa_deg: Optional[float] = None
    processing_time_sec: Optional[float] = None
    n_frames: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'detected': self.detected,
            'confidence': self.confidence,
            'detection_method': self.detection_method,
            'snr_db': self.snr_db,
            'harmonic_score': self.harmonic_score,
            'temporal_score': self.temporal_score,
            'doa_angle_deg': self.doa_angle_deg,
            'doa_std_deg': self.doa_std_deg,
            'mean_doa_deg': self.mean_doa_deg,
            'processing_time_sec': self.processing_time_sec,
            'n_frames': self.n_frames,
        }


class DetectionProcessor:
    """
    Audio detection processor with configurable signal processing methods.

    Supports multiple detection methods:
    - Energy Likelihood: Multi-evidence detector (SNR + Harmonic + Temporal)
    - GCC-PHAT DOA: Direction of Arrival estimation for stereo audio
    - Harmonic Filter: Harmonic filtering for noise reduction
    - Combined: All methods combined for maximum confidence
    - ML Model: ONNX-based machine learning model for detection
    """

    def __init__(self, config: Dict):
        """
        Initialize detection processor with configuration.

        Parameters
        ----------
        config : dict
            Configuration dictionary with detection parameters
        """
        self.config = config
        self.method = config.get('method', 'combined')
        self.use_ml_model = config.get('use_ml_model', False) or self.method == 'ml_model'
        self.ml_model_path = config.get('ml_model_path', None)

        # Initialize ML model if requested
        if self.use_ml_model:
            self.ml_model = self._load_ml_model()
        else:
            self.ml_model = None

        # Initialize detector if using energy likelihood method
        if self.method in ['energy_likelihood', 'combined'] and not self.use_ml_model:
            self.detector = EnergyLikelihoodDetector(
                f0=config.get('fundamental_freq_hz', 150.0),
                n_harmonics=config.get('n_harmonics', 7),
                coarse_band_hz=(
                    config.get('freq_band_low_hz', 100.0),
                    config.get('freq_band_high_hz', 5000.0)
                ),
                harmonic_bw_hz=config.get('harmonic_bandwidth_hz', 40.0),
                weight_snr=config.get('weight_snr', 0.4),
                weight_harmonic=config.get('weight_harmonic', 0.3),
                weight_temporal=config.get('weight_temporal', 0.3),
                snr_range_db=(
                    config.get('snr_min_db', 0.0),
                    config.get('snr_max_db', 30.0)
                ),
                harmonic_min_snr_db=config.get('harmonic_min_snr_db', 3.0),
                temporal_window=config.get('temporal_window', 5),
                confidence_threshold=config.get('confidence_threshold', 0.75)
            )
        else:
            self.detector = None

        logger.info(f"DetectionProcessor initialized with method: {self.method}, ML model: {self.use_ml_model}")

    def _load_ml_model(self):
        """Load ONNX ML model for detection."""
        try:
            import onnxruntime as ort
            from pathlib import Path
            import os

            # Get model path
            if self.ml_model_path:
                model_path = Path(self.ml_model_path)
            else:
                # Default model location
                base_dir = Path(__file__).parent.parent
                model_path = base_dir / 'drone_33d_mlp.onnx'

            if not model_path.exists():
                logger.warning(f"ML model not found at {model_path}, falling back to signal processing")
                return None

            # Load ONNX model
            session = ort.InferenceSession(str(model_path))
            logger.info(f"Loaded ML model from {model_path}")
            return session

        except ImportError:
            logger.warning("onnxruntime not installed, ML model detection unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            return None

    def process_audio(
        self,
        audio: np.ndarray,
        fs: float,
        is_stereo: bool = False
    ) -> DetectionResult:
        """
        Process audio and perform drone detection.

        Parameters
        ----------
        audio : np.ndarray
            Audio signal array
            - Mono: shape [n_samples]
            - Stereo: shape [n_samples, 2]
        fs : float
            Sampling rate in Hz
        is_stereo : bool
            Whether audio is stereo

        Returns
        -------
        result : DetectionResult
            Detection results with confidence and metrics
        """
        import time
        start_time = time.time()

        logger.info(f"Processing audio: {len(audio)} samples, fs={fs} Hz, stereo={is_stereo}")

        # Use ML model if available
        if self.use_ml_model and self.ml_model:
            return self._detect_with_ml_model(audio, fs, is_stereo)

        # Frame and window the audio
        frame_length_ms = self.config.get('frame_length_ms', 64.0)
        hop_length_ms = self.config.get('hop_length_ms', 32.0)

        doa_angles = None

        if is_stereo and audio.ndim == 2:
            # Multi-channel framing for DOA estimation
            frames_multichannel, frame_times = self._frame_multichannel(
                audio, fs, frame_length_ms, hop_length_ms
            )

            # Perform DOA estimation if requested
            if self.method in ['gcc_phat_doa', 'combined']:
                doa_angles = self._estimate_doa(frames_multichannel, fs)

            # Average channels for detection
            frames = np.mean(frames_multichannel, axis=2)
        else:
            # Mono framing
            from .framing_windowing import frame_and_window
            frames, frame_times = frame_and_window(
                audio, fs,
                frame_length_ms=frame_length_ms,
                hop_length_ms=hop_length_ms,
                window_type='hann'
            )

        # Compute FFT
        freqs, spectrum, magnitude, magnitude_db = compute_fft_per_frame(
            frames, fs,
            nfft=1024,
            remove_dc=True
        )

        logger.info(f"FFT computed: {frames.shape[0]} frames, {len(freqs)} frequency bins")

        # Apply harmonic filtering if requested
        if self.method in ['harmonic_filter', 'combined']:
            magnitude = self._apply_harmonic_filter(magnitude, freqs)

        # Perform detection
        result = self._detect(freqs, magnitude, doa_angles)

        # Add processing metadata
        result.processing_time_sec = time.time() - start_time
        result.n_frames = len(frames)

        logger.info(f"Detection complete: detected={result.detected}, "
                   f"confidence={result.confidence:.3f}, method={result.detection_method}")

        return result

    def _frame_multichannel(
        self,
        audio: np.ndarray,
        fs: float,
        frame_length_ms: float,
        hop_length_ms: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Frame multi-channel audio."""
        from .framing_windowing import get_window

        n_samples, n_channels = audio.shape
        frame_length = int(round(fs * frame_length_ms / 1000.0))
        hop_length = int(round(fs * hop_length_ms / 1000.0))

        n_frames = 1 + (n_samples - frame_length) // hop_length
        frames = np.zeros((n_frames, frame_length, n_channels), dtype=np.float64)

        for i in range(n_frames):
            start_idx = i * hop_length
            end_idx = start_idx + frame_length
            frames[i, :, :] = audio[start_idx:end_idx, :]

        window = get_window('hann', frame_length)
        frames = frames * window[None, :, None]

        frame_times = (np.arange(n_frames) * hop_length + frame_length / 2.0) / fs

        return frames, frame_times

    def _estimate_doa(
        self,
        frames_multichannel: np.ndarray,
        fs: float
    ) -> Optional[np.ndarray]:
        """Estimate Direction of Arrival using GCC-PHAT."""
        try:
            mic_spacing = self.config.get('mic_spacing_m', 0.14)

            doa_angles, tdoa_series = estimate_doa_gcc_phat(
                frames_multichannel, fs, mic_spacing,
                ref_channel=0,
                c=343.0,
                interp=16,
                robust_averaging=True
            )

            logger.info(f"DOA estimated: mean={np.degrees(doa_angles).mean():.1f}°, "
                       f"std={np.degrees(doa_angles).std():.1f}°")

            return doa_angles
        except Exception as e:
            logger.error(f"DOA estimation failed: {e}")
            return None

    def _apply_harmonic_filter(
        self,
        magnitude: np.ndarray,
        freqs: np.ndarray
    ) -> np.ndarray:
        """Apply harmonic filtering to magnitude spectrum."""
        try:
            f0 = self.config.get('fundamental_freq_hz', 150.0)
            n_harmonics = self.config.get('n_harmonics', 7)
            harmonic_bw_hz = self.config.get('harmonic_bandwidth_hz', 40.0)

            # Create harmonic mask
            harmonic_mask = make_harmonic_mask(
                freqs, f0, n_harmonics, harmonic_bw_hz
            )

            # Apply mask to magnitude (zero out non-harmonic bins)
            filtered_magnitude = magnitude.copy()
            filtered_magnitude[:, ~harmonic_mask] = 0

            logger.info(f"Harmonic filter applied: f0={f0} Hz, {n_harmonics} harmonics")

            return filtered_magnitude
        except Exception as e:
            logger.error(f"Harmonic filtering failed: {e}")
            return magnitude

    def _detect(
        self,
        freqs: np.ndarray,
        magnitude: np.ndarray,
        doa_angles: Optional[np.ndarray]
    ) -> DetectionResult:
        """Perform detection using configured method."""

        if self.method in ['energy_likelihood', 'combined']:
            # Use multi-evidence detector
            confidences = []
            snr_values = []
            harmonic_scores = []
            temporal_scores = []

            for i in range(len(magnitude)):
                confidence, detected, details = self.detector.score_frame(
                    freqs, magnitude[i]
                )
                confidences.append(confidence)
                snr_values.append(details['snr_db'])
                harmonic_scores.append(details['harmonic_score'])
                temporal_scores.append(details['temporal_score'])

            # Aggregate results
            mean_confidence = np.mean(confidences)
            max_confidence = np.max(confidences)
            detection_rate = np.mean([c >= self.config.get('confidence_threshold', 0.75)
                                     for c in confidences])

            # Overall detection: at least 30% of frames
            overall_detected = detection_rate >= 0.3

            result = DetectionResult(
                detected=overall_detected,
                confidence=mean_confidence,
                detection_method=self.method,
                snr_db=np.mean(snr_values),
                harmonic_score=np.mean(harmonic_scores),
                temporal_score=np.mean(temporal_scores)
            )

        elif self.method == 'gcc_phat_doa':
            # DOA-based detection (check if angle is stable)
            if doa_angles is not None:
                doa_std = np.degrees(doa_angles).std()
                # If angle is stable (low std), more confident detection
                confidence = np.clip(1.0 - doa_std / 45.0, 0.0, 1.0)
                detected = confidence >= self.config.get('confidence_threshold', 0.75)
            else:
                confidence = 0.0
                detected = False

            result = DetectionResult(
                detected=detected,
                confidence=confidence,
                detection_method=self.method
            )

        elif self.method == 'harmonic_filter':
            # Simple energy-based detection after filtering
            total_energy = np.mean(magnitude ** 2)
            # Normalize to 0-1 range (heuristic)
            confidence = np.clip(total_energy / 10.0, 0.0, 1.0)
            detected = confidence >= self.config.get('confidence_threshold', 0.75)

            result = DetectionResult(
                detected=detected,
                confidence=confidence,
                detection_method=self.method
            )

        else:
            # Default: no detection
            result = DetectionResult(
                detected=False,
                confidence=0.0,
                detection_method='none'
            )

        # Add DOA information if available
        if doa_angles is not None:
            doa_degrees = np.degrees(doa_angles)
            result.doa_angle_deg = float(doa_degrees.mean())
            result.doa_std_deg = float(doa_degrees.std())
            result.mean_doa_deg = float(doa_degrees.mean())

        return result

    def _detect_with_ml_model(
        self,
        audio: np.ndarray,
        fs: float,
        is_stereo: bool
    ) -> DetectionResult:
        """Detect using ML model (ONNX)."""
        import time
        start_time = time.time()

        try:
            # Preprocess audio for ML model
            # Convert to mono if stereo
            if is_stereo and audio.ndim > 1:
                audio = np.mean(audio, axis=1)

            # Normalize audio
            audio = audio / (np.max(np.abs(audio)) + 1e-8)

            # Frame and window the audio
            frame_length_ms = self.config.get('frame_length_ms', 64.0)
            hop_length_ms = self.config.get('hop_length_ms', 32.0)
            from .framing_windowing import frame_and_window
            frames, frame_times = frame_and_window(
                audio, fs,
                frame_length_ms=frame_length_ms,
                hop_length_ms=hop_length_ms,
                window_type='hann'
            )

            # Compute FFT features
            from .fft import compute_fft_per_frame
            freqs, spectrum, magnitude, magnitude_db = compute_fft_per_frame(
                frames, fs,
                nfft=1024,
                remove_dc=True
            )

            # Prepare features for ML model (use magnitude spectrum)
            # Average across frames or use last frame
            features = np.mean(magnitude_db, axis=0)
            features = features.reshape(1, -1).astype(np.float32)

            # Run inference
            input_name = self.ml_model.get_inputs()[0].name
            output = self.ml_model.run(None, {input_name: features})

            # Get prediction (assuming binary classification)
            confidence = float(output[0][0][1] if output[0].shape[1] > 1 else output[0][0][0])
            detected = confidence >= self.config.get('confidence_threshold', 0.75)

            # Estimate DOA if stereo (re-frame for DOA estimation)
            doa_angle_deg = None
            if is_stereo and audio.ndim > 1:
                try:
                    # Re-frame original stereo audio for DOA
                    frames_multichannel, _ = self._frame_multichannel(
                        audio, fs,
                        frame_length_ms,
                        hop_length_ms
                    )
                    doa_angles = self._estimate_doa(frames_multichannel, fs)
                    if doa_angles is not None:
                        doa_angle_deg = float(np.degrees(doa_angles).mean())
                except Exception as e:
                    logger.warning(f"DOA estimation failed in ML model detection: {e}")

            result = DetectionResult(
                detected=detected,
                confidence=confidence,
                detection_method='ml_model',
                doa_angle_deg=doa_angle_deg,
                processing_time_sec=time.time() - start_time,
                n_frames=len(frames)
            )

            logger.info(f"ML model detection: detected={detected}, confidence={confidence:.3f}")
            return result

        except Exception as e:
            logger.error(f"ML model detection failed: {e}", exc_info=True)
            # Fallback to signal processing
            return DetectionResult(
                detected=False,
                confidence=0.0,
                detection_method='ml_model_error',
                processing_time_sec=time.time() - start_time
            )

    def reset(self):
        """Reset detector state."""
        if self.detector:
            self.detector.reset()
            logger.info("Detector state reset")
