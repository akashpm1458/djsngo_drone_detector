"""
Management command to initialize default detection configurations.

Usage:
    python manage.py init_detection_configs
"""
from django.core.management.base import BaseCommand
from core.models import DetectionConfig


class Command(BaseCommand):
    help = 'Initialize default detection configurations'

    def handle(self, *args, **options):
        """Create default detection configurations."""

        self.stdout.write('Initializing default detection configurations...')

        # Check if configurations already exist
        if DetectionConfig.objects.exists():
            self.stdout.write(
                self.style.WARNING('Detection configurations already exist. Skipping initialization.')
            )
            return

        # Create default configurations
        configs = [
            {
                'config_name': 'Default Combined',
                'method': DetectionConfig.METHOD_COMBINED,
                'is_active': True,
                'fundamental_freq_hz': 150.0,
                'n_harmonics': 7,
                'confidence_threshold': 0.75,
                'freq_band_low_hz': 100.0,
                'freq_band_high_hz': 5000.0,
                'harmonic_bandwidth_hz': 40.0,
                'snr_min_db': 0.0,
                'snr_max_db': 30.0,
                'harmonic_min_snr_db': 3.0,
                'temporal_window': 5,
                'weight_snr': 0.4,
                'weight_harmonic': 0.3,
                'weight_temporal': 0.3,
                'mic_spacing_m': 0.14,
                'frame_length_ms': 64.0,
                'hop_length_ms': 32.0,
                'created_by': 'system'
            },
            {
                'config_name': 'Energy Likelihood Only',
                'method': DetectionConfig.METHOD_ENERGY_LIKELIHOOD,
                'is_active': False,
                'fundamental_freq_hz': 150.0,
                'n_harmonics': 7,
                'confidence_threshold': 0.80,
                'freq_band_low_hz': 100.0,
                'freq_band_high_hz': 2000.0,
                'harmonic_bandwidth_hz': 40.0,
                'snr_min_db': 0.0,
                'snr_max_db': 30.0,
                'harmonic_min_snr_db': 3.0,
                'temporal_window': 7,
                'weight_snr': 0.4,
                'weight_harmonic': 0.3,
                'weight_temporal': 0.3,
                'mic_spacing_m': 0.14,
                'frame_length_ms': 64.0,
                'hop_length_ms': 32.0,
                'created_by': 'system'
            },
            {
                'config_name': 'GCC-PHAT DOA',
                'method': DetectionConfig.METHOD_GCC_PHAT_DOA,
                'is_active': False,
                'fundamental_freq_hz': 150.0,
                'n_harmonics': 5,
                'confidence_threshold': 0.70,
                'freq_band_low_hz': 100.0,
                'freq_band_high_hz': 5000.0,
                'harmonic_bandwidth_hz': 50.0,
                'snr_min_db': 0.0,
                'snr_max_db': 30.0,
                'harmonic_min_snr_db': 3.0,
                'temporal_window': 5,
                'weight_snr': 0.4,
                'weight_harmonic': 0.3,
                'weight_temporal': 0.3,
                'mic_spacing_m': 0.10,  # 10 cm for closer mics
                'frame_length_ms': 64.0,
                'hop_length_ms': 32.0,
                'created_by': 'system'
            },
            {
                'config_name': 'High Sensitivity',
                'method': DetectionConfig.METHOD_COMBINED,
                'is_active': False,
                'fundamental_freq_hz': 150.0,
                'n_harmonics': 10,
                'confidence_threshold': 0.60,  # Lower threshold
                'freq_band_low_hz': 50.0,  # Wider band
                'freq_band_high_hz': 6000.0,
                'harmonic_bandwidth_hz': 60.0,  # Wider bandwidth
                'snr_min_db': -5.0,  # Allow lower SNR
                'snr_max_db': 35.0,
                'harmonic_min_snr_db': 2.0,  # Lower threshold
                'temporal_window': 3,  # Faster response
                'weight_snr': 0.3,
                'weight_harmonic': 0.4,
                'weight_temporal': 0.3,
                'mic_spacing_m': 0.14,
                'frame_length_ms': 64.0,
                'hop_length_ms': 32.0,
                'created_by': 'system'
            },
        ]

        for config_data in configs:
            config = DetectionConfig.objects.create(**config_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created configuration: {config.config_name}')
            )

        self.stdout.write(self.style.SUCCESS('Successfully initialized detection configurations!'))
