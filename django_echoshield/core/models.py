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
