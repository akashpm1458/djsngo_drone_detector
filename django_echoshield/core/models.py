"""
Core Django models for EchoShield.

Converted from SQLite schema to Django ORM models.
"""
from django.db import models
from django.utils import timezone
import uuid


class Event(models.Model):
    """
    Main event storage model.
    Represents a single detection event from an edge node.
    """

    # Latency status choices
    LATENCY_NORMAL = 'normal'
    LATENCY_DELAYED = 'delayed'
    LATENCY_OBSOLETE = 'obsolete'
    LATENCY_STATUS_CHOICES = [
        (LATENCY_NORMAL, 'Normal'),
        (LATENCY_DELAYED, 'Delayed'),
        (LATENCY_OBSOLETE, 'Obsolete'),
    ]

    # Sensor type choices
    SENSOR_ACOUSTIC = 'acoustic'
    SENSOR_VISION = 'vision'
    SENSOR_HYBRID = 'hybrid'
    SENSOR_TYPE_CHOICES = [
        (SENSOR_ACOUSTIC, 'Acoustic'),
        (SENSOR_VISION, 'Vision'),
        (SENSOR_HYBRID, 'Hybrid'),
    ]

    # Validity status choices
    VALIDITY_VALID = 'valid'
    VALIDITY_INVALID = 'invalid'
    VALIDITY_UNKNOWN = 'unknown'
    VALIDITY_STATUS_CHOICES = [
        (VALIDITY_VALID, 'Valid'),
        (VALIDITY_INVALID, 'Invalid'),
        (VALIDITY_UNKNOWN, 'Unknown'),
    ]

    # Location method choices
    LOC_BEARING_ONLY = 'LOC_BEARING_ONLY'
    LOC_ACOUSTIC_TRIANGULATION = 'LOC_ACOUSTIC_TRIANGULATION'
    LOCATION_METHOD_CHOICES = [
        (LOC_BEARING_ONLY, 'Bearing Only'),
        (LOC_ACOUSTIC_TRIANGULATION, 'Acoustic Triangulation'),
    ]

    # Primary Key
    id = models.BigAutoField(primary_key=True)

    # Core Event Identity
    event_id = models.CharField(max_length=255, unique=True, db_index=True,
                                 default=uuid.uuid4, editable=False)
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPE_CHOICES)
    sensor_node_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)

    # Timestamps (nanoseconds - using BigInteger for precision)
    ts_ns = models.BigIntegerField(db_index=True, help_text="Detection timestamp (nanoseconds)")
    rx_ns = models.BigIntegerField(db_index=True, help_text="Server receipt timestamp (nanoseconds)")
    latency_ns = models.BigIntegerField(help_text="Latency: rx_ns - ts_ns (nanoseconds)")
    latency_status = models.CharField(max_length=20, choices=LATENCY_STATUS_CHOICES)
    clock_skew_ns = models.BigIntegerField(null=True, blank=True,
                                           help_text="Clock drift measurement (nanoseconds)")

    # Geolocation
    lat = models.FloatField(null=True, blank=True, help_text="Latitude (decimal degrees)")
    lon = models.FloatField(null=True, blank=True, help_text="Longitude (decimal degrees)")
    error_radius_m = models.FloatField(null=True, blank=True, help_text="Location accuracy (meters)")

    # Bearing Information
    bearing_deg = models.FloatField(null=True, blank=True, help_text="Bearing angle (0-360 degrees)")
    bearing_conf = models.FloatField(null=True, blank=True, help_text="Bearing confidence (0.0-1.0)")
    bearing_std_deg = models.FloatField(null=True, blank=True,
                                        help_text="Bearing standard deviation (degrees)")

    # Detection Details
    n_objects = models.IntegerField(null=True, blank=True, help_text="Number of objects detected")
    event_code = models.CharField(max_length=50, null=True, blank=True, help_text="Event type code")
    location_method = models.CharField(max_length=50, choices=LOCATION_METHOD_CHOICES,
                                       null=True, blank=True)
    packet_version = models.IntegerField(null=True, blank=True)

    # Post-Processing Results
    validity_status = models.CharField(max_length=20, choices=VALIDITY_STATUS_CHOICES,
                                       default=VALIDITY_UNKNOWN)
    duplicate_flag = models.BooleanField(default=False, help_text="Is this a duplicate event?")
    object_track_id = models.CharField(max_length=255, db_index=True, null=True, blank=True,
                                       help_text="FK to Track")

    # GCC-PHAT Metadata (stored as JSON)
    gcc_phat_metadata = models.JSONField(null=True, blank=True,
                                        help_text="GCC-PHAT bearing estimation metadata")

    # Detection Method and Results
    detection_method = models.CharField(max_length=50, null=True, blank=True,
                                       help_text="Signal processing method used")
    detection_confidence = models.FloatField(null=True, blank=True,
                                            help_text="Overall detection confidence (0.0-1.0)")
    snr_db = models.FloatField(null=True, blank=True,
                              help_text="Signal-to-Noise Ratio in dB")
    harmonic_score = models.FloatField(null=True, blank=True,
                                      help_text="Harmonic integrity score (0.0-1.0)")
    temporal_score = models.FloatField(null=True, blank=True,
                                      help_text="Temporal stability score (0.0-1.0)")
    doa_angle_deg = models.FloatField(null=True, blank=True,
                                     help_text="Direction of Arrival angle in degrees")

    # Audit
    raw_wire_json = models.JSONField(help_text="Original WirePacket JSON")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        ordering = ['-rx_ns']
        indexes = [
            models.Index(fields=['sensor_node_id', 'ts_ns'], name='idx_node_ts'),
            models.Index(fields=['object_track_id'], name='idx_track'),
        ]
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def __str__(self):
        return f"Event {self.event_id[:8]} - {self.sensor_type} @ {self.sensor_node_id}"

    @property
    def latency_ms(self):
        """Return latency in milliseconds for display."""
        return self.latency_ns / 1_000_000 if self.latency_ns else None

    @property
    def timestamp_datetime(self):
        """Convert ts_ns to datetime object."""
        return timezone.datetime.fromtimestamp(self.ts_ns / 1_000_000_000, tz=timezone.utc)


class Track(models.Model):
    """
    Aggregated multi-node tracks.
    Represents a unified detection track from multiple edge nodes.
    """

    # Status choices
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    # Method choices
    METHOD_BEARING_ONLY = 'bearing_only'
    METHOD_TRIANGULATION = 'triangulation'
    METHOD_CHOICES = [
        (METHOD_BEARING_ONLY, 'Bearing Only'),
        (METHOD_TRIANGULATION, 'Triangulation'),
    ]

    # Primary Key
    track_id = models.CharField(max_length=255, primary_key=True)

    # Method
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, null=True, blank=True)

    # Time Range
    first_ts_ns = models.BigIntegerField(help_text="First detection timestamp (nanoseconds)")
    last_ts_ns = models.BigIntegerField(db_index=True,
                                        help_text="Latest detection timestamp (nanoseconds)")

    # Aggregated Position
    aggregated_bearing_deg = models.FloatField(null=True, blank=True,
                                               help_text="Averaged bearing from all contributors")
    aggregated_lat = models.FloatField(null=True, blank=True,
                                       help_text="Future: triangulated latitude")
    aggregated_lon = models.FloatField(null=True, blank=True,
                                       help_text="Future: triangulated longitude")
    aggregation_conf = models.FloatField(null=True, blank=True,
                                        help_text="Aggregation confidence (0.0-1.0)")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tracks'
        ordering = ['-last_ts_ns']
        indexes = [
            models.Index(fields=['last_ts_ns'], name='idx_last_ts'),
        ]
        verbose_name = 'Track'
        verbose_name_plural = 'Tracks'

    def __str__(self):
        return f"Track {self.track_id} - {self.status}"

    @property
    def duration_ns(self):
        """Track duration in nanoseconds."""
        return self.last_ts_ns - self.first_ts_ns if self.first_ts_ns and self.last_ts_ns else None

    @property
    def duration_seconds(self):
        """Track duration in seconds."""
        duration = self.duration_ns
        return duration / 1_000_000_000 if duration else None


class TrackContributor(models.Model):
    """
    Multi-node detection links.
    Links individual events to aggregated tracks.
    """

    # Foreign Keys
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='contributors',
                              db_column='track_id')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='track_contributions',
                              db_column='event_id')

    # Contributor details
    sensor_node_id = models.CharField(max_length=255)
    bearing_deg = models.FloatField(null=True, blank=True)
    ts_ns = models.BigIntegerField()

    class Meta:
        db_table = 'track_contributors'
        unique_together = ['track', 'event']
        verbose_name = 'Track Contributor'
        verbose_name_plural = 'Track Contributors'

    def __str__(self):
        return f"Contributor {self.sensor_node_id} to {self.track.track_id}"


class DetectionConfig(models.Model):
    """
    Signal processing configuration for edge nodes.
    Stores user-selectable detection methods and parameters.
    """

    # Detection method choices
    METHOD_ENERGY_LIKELIHOOD = 'energy_likelihood'
    METHOD_GCC_PHAT_DOA = 'gcc_phat_doa'
    METHOD_HARMONIC_FILTER = 'harmonic_filter'
    METHOD_COMBINED = 'combined'
    METHOD_ML_MODEL = 'ml_model'
    METHOD_CHOICES = [
        (METHOD_ENERGY_LIKELIHOOD, 'Energy Likelihood Detector'),
        (METHOD_GCC_PHAT_DOA, 'GCC-PHAT Direction of Arrival'),
        (METHOD_HARMONIC_FILTER, 'Harmonic Filter Only'),
        (METHOD_COMBINED, 'Combined Multi-Evidence'),
        (METHOD_ML_MODEL, 'ML Model (ONNX)'),
    ]

    # Primary Key
    id = models.AutoField(primary_key=True)

    # Configuration identity
    config_name = models.CharField(max_length=100, unique=True,
                                   help_text="Unique name for this configuration")
    is_active = models.BooleanField(default=False,
                                   help_text="Is this the active configuration?")

    # Detection method
    method = models.CharField(max_length=50, choices=METHOD_CHOICES,
                             default=METHOD_COMBINED,
                             help_text="Signal processing method to use")

    # Core parameters
    fundamental_freq_hz = models.FloatField(default=150.0,
                                           help_text="Expected fundamental frequency (Hz)")
    n_harmonics = models.IntegerField(default=7,
                                     help_text="Number of harmonics to analyze")
    confidence_threshold = models.FloatField(default=0.75,
                                           help_text="Detection threshold (0.0-1.0)")

    # Frequency band
    freq_band_low_hz = models.FloatField(default=100.0,
                                        help_text="Lower frequency bound (Hz)")
    freq_band_high_hz = models.FloatField(default=5000.0,
                                         help_text="Upper frequency bound (Hz)")

    # Harmonic parameters
    harmonic_bandwidth_hz = models.FloatField(default=40.0,
                                             help_text="Bandwidth per harmonic (Hz)")

    # SNR parameters
    snr_min_db = models.FloatField(default=0.0,
                                  help_text="Minimum SNR for normalization (dB)")
    snr_max_db = models.FloatField(default=30.0,
                                  help_text="Maximum SNR for normalization (dB)")
    harmonic_min_snr_db = models.FloatField(default=3.0,
                                           help_text="Minimum SNR per harmonic (dB)")

    # Temporal parameters
    temporal_window = models.IntegerField(default=5,
                                         help_text="Number of frames for temporal smoothing")

    # Evidence weights
    weight_snr = models.FloatField(default=0.4,
                                  help_text="Weight for SNR evidence")
    weight_harmonic = models.FloatField(default=0.3,
                                       help_text="Weight for harmonic evidence")
    weight_temporal = models.FloatField(default=0.3,
                                       help_text="Weight for temporal evidence")

    # DOA parameters
    mic_spacing_m = models.FloatField(default=0.14,
                                     help_text="Microphone spacing in meters")

    # Framing parameters
    frame_length_ms = models.FloatField(default=64.0,
                                       help_text="Frame length in milliseconds")
    hop_length_ms = models.FloatField(default=32.0,
                                     help_text="Hop length in milliseconds")

    # ML Model parameters
    ml_model_path = models.CharField(max_length=255, null=True, blank=True,
                                    help_text="Path to ONNX model file (e.g., drone_33d_mlp.onnx)")
    use_ml_model = models.BooleanField(default=False,
                                      help_text="Use ML model for detection instead of signal processing")

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True,
                                 help_text="User who created this configuration")

    class Meta:
        db_table = 'detection_configs'
        ordering = ['-created_at']
        verbose_name = 'Detection Configuration'
        verbose_name_plural = 'Detection Configurations'

    def __str__(self):
        return f"{self.config_name} - {self.get_method_display()}"

    def save(self, *args, **kwargs):
        """Ensure only one active configuration at a time."""
        if self.is_active:
            # Deactivate all other configs
            DetectionConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
