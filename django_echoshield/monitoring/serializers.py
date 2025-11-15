"""
Django REST Framework serializers for monitoring app.

Handles WirePacket and Canonical Event serialization/deserialization.
"""
from rest_framework import serializers
from core.models import Event, Track, TrackContributor


class LocationIntSerializer(serializers.Serializer):
    """
    Serializer for compact location format.

    Location is stored as integers for compact wire transmission:
    - lat_int: latitude * 100000 (5 decimal places precision)
    - lon_int: longitude * 100000
    - error_radius_m: GPS accuracy in meters
    """
    lat_int = serializers.IntegerField(help_text="Latitude * 1e5")
    lon_int = serializers.IntegerField(help_text="Longitude * 1e5")
    error_radius_m = serializers.IntegerField(help_text="Location accuracy (meters)")

    def to_representation(self, instance):
        """Convert to wire format."""
        if isinstance(instance, dict):
            return instance
        return {
            'lat_int': instance.lat_int,
            'lon_int': instance.lon_int,
            'error_radius_m': instance.error_radius_m
        }


class GccPhatMetadataSerializer(serializers.Serializer):
    """
    Serializer for GCC-PHAT bearing estimation metadata.
    """
    method = serializers.CharField(default='GCC_PHAT_TDOA')
    paired_node_id = serializers.CharField()
    baseline_distance_m = serializers.FloatField()
    tdoa_sec = serializers.FloatField()
    baseline_bearing_deg = serializers.FloatField()


class WirePacketSerializer(serializers.Serializer):
    """
    Serializer for WirePacket wire protocol format.

    This is the compact format used for transmission from edge nodes
    to the ingest API.
    """
    event_id = serializers.CharField(max_length=255)
    sensor_type = serializers.ChoiceField(
        choices=['acoustic', 'vision', 'hybrid']
    )
    ts_ns = serializers.IntegerField(help_text="Detection timestamp (nanoseconds)")
    sensor_node_id = serializers.CharField(max_length=255)
    location = LocationIntSerializer()
    bearing_deg = serializers.IntegerField(
        required=False, allow_null=True,
        help_text="Bearing * 100 (e.g., 4500 = 45.00 degrees)"
    )
    bearing_confidence = serializers.IntegerField(
        min_value=0, max_value=100,
        help_text="Confidence * 100 (0-100)"
    )
    n_objects_detected = serializers.IntegerField(min_value=0)
    event_code = serializers.IntegerField()
    location_method = serializers.ChoiceField(
        required=False, allow_null=True,
        choices=['LOC_BEARING_ONLY', 'LOC_ACOUSTIC_TRIANGULATION']
    )
    packet_version = serializers.IntegerField(required=False, allow_null=True, default=1)
    gcc_phat_metadata = GccPhatMetadataSerializer(required=False, allow_null=True)


class CanonicalEventSerializer(serializers.Serializer):
    """
    Serializer for Canonical Event format.

    This is the human-readable format stored in the database.
    All fixed-point integers are converted to floats.
    """
    # From WirePacket
    event_id = serializers.CharField()
    sensor_type = serializers.CharField()
    sensor_node_id = serializers.CharField()
    ts_ns = serializers.IntegerField()

    # Location (converted from fixed-point)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    error_radius_m = serializers.FloatField(required=False, allow_null=True)

    # Bearing (converted from fixed-point)
    bearing_deg = serializers.FloatField(required=False, allow_null=True)
    bearing_conf = serializers.FloatField(required=False, allow_null=True)

    # Detection details
    n_objects = serializers.IntegerField(required=False, allow_null=True)
    event_code = serializers.CharField(required=False, allow_null=True)
    location_method = serializers.CharField(required=False, allow_null=True)
    packet_version = serializers.IntegerField(required=False, allow_null=True)

    # Server-side additions
    rx_ns = serializers.IntegerField()
    latency_ns = serializers.IntegerField()
    latency_status = serializers.CharField()

    # GCC-PHAT metadata (if present)
    gcc_phat_metadata = GccPhatMetadataSerializer(required=False, allow_null=True)


class EventSerializer(serializers.ModelSerializer):
    """
    Full Event model serializer for API responses.
    """
    latency_ms = serializers.FloatField(read_only=True)
    timestamp_datetime = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = [
            'id', 'event_id', 'created_at', 'updated_at',
            'latency_ms', 'timestamp_datetime'
        ]


class TrackContributorSerializer(serializers.ModelSerializer):
    """Serializer for track contributors."""

    class Meta:
        model = TrackContributor
        fields = ['sensor_node_id', 'bearing_deg', 'ts_ns']


class TrackSerializer(serializers.ModelSerializer):
    """
    Track model serializer with contributors.
    """
    contributors = TrackContributorSerializer(many=True, read_only=True)
    contributor_count = serializers.SerializerMethodField()
    duration_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = Track
        fields = '__all__'
        read_only_fields = ['track_id', 'created_at', 'updated_at']

    def get_contributor_count(self, obj):
        """Get the number of contributors to this track."""
        return obj.contributors.count()
