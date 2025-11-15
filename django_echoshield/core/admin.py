"""
Django admin interface for EchoShield core models.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Track, TrackContributor, DetectionConfig


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin interface for Event model."""

    list_display = [
        'event_id_short', 'sensor_type', 'sensor_node_id', 'latency_display',
        'latency_status', 'bearing_deg', 'bearing_conf', 'duplicate_flag',
        'object_track_id', 'created_at'
    ]
    list_filter = [
        'sensor_type', 'latency_status', 'validity_status', 'duplicate_flag',
        'location_method', 'created_at'
    ]
    search_fields = ['event_id', 'sensor_node_id', 'object_track_id']
    readonly_fields = [
        'event_id', 'ts_ns', 'rx_ns', 'latency_ns', 'created_at', 'updated_at',
        'raw_wire_json', 'gcc_phat_metadata'
    ]
    fieldsets = [
        ('Identity', {
            'fields': ['event_id', 'sensor_type', 'sensor_node_id']
        }),
        ('Timestamps', {
            'fields': ['ts_ns', 'rx_ns', 'latency_ns', 'latency_status', 'clock_skew_ns']
        }),
        ('Location', {
            'fields': ['lat', 'lon', 'error_radius_m', 'location_method']
        }),
        ('Bearing', {
            'fields': ['bearing_deg', 'bearing_conf', 'bearing_std_deg', 'gcc_phat_metadata']
        }),
        ('Detection', {
            'fields': ['n_objects', 'event_code', 'packet_version']
        }),
        ('Post-Processing', {
            'fields': ['validity_status', 'duplicate_flag', 'object_track_id']
        }),
        ('Audit', {
            'fields': ['raw_wire_json', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def event_id_short(self, obj):
        """Display shortened event ID."""
        return obj.event_id[:8] + '...'
    event_id_short.short_description = 'Event ID'

    def latency_display(self, obj):
        """Display latency in milliseconds with color coding."""
        if obj.latency_ns is None:
            return '-'
        latency_ms = obj.latency_ms
        if obj.latency_status == Event.LATENCY_NORMAL:
            color = 'green'
        elif obj.latency_status == Event.LATENCY_DELAYED:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.2f} ms</span>',
            color, latency_ms
        )
    latency_display.short_description = 'Latency'

    def has_add_permission(self, request):
        """Disable manual event creation (events come from API)."""
        return False


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    """Admin interface for Track model."""

    list_display = [
        'track_id', 'method', 'status', 'contributor_count',
        'aggregated_bearing_deg', 'aggregation_conf', 'duration_display',
        'created_at', 'updated_at'
    ]
    list_filter = ['method', 'status', 'created_at']
    search_fields = ['track_id']
    readonly_fields = ['track_id', 'created_at', 'updated_at', 'duration_display']
    fieldsets = [
        ('Identity', {
            'fields': ['track_id', 'method', 'status']
        }),
        ('Time Range', {
            'fields': ['first_ts_ns', 'last_ts_ns', 'duration_display']
        }),
        ('Aggregated Position', {
            'fields': [
                'aggregated_bearing_deg', 'aggregated_lat', 'aggregated_lon',
                'aggregation_conf'
            ]
        }),
        ('Audit', {
            'fields': ['created_at', 'updated_at']
        }),
    ]
    inlines = []

    def contributor_count(self, obj):
        """Display number of contributing events."""
        return obj.contributors.count()
    contributor_count.short_description = 'Contributors'

    def duration_display(self, obj):
        """Display track duration in seconds."""
        duration = obj.duration_seconds
        if duration is None:
            return '-'
        return f"{duration:.2f} s"
    duration_display.short_description = 'Duration'


@admin.register(TrackContributor)
class TrackContributorAdmin(admin.ModelAdmin):
    """Admin interface for TrackContributor model."""

    list_display = ['track', 'event', 'sensor_node_id', 'bearing_deg', 'ts_ns']
    list_filter = ['sensor_node_id']
    search_fields = ['track__track_id', 'event__event_id', 'sensor_node_id']
    readonly_fields = ['track', 'event', 'sensor_node_id', 'bearing_deg', 'ts_ns']

    def has_add_permission(self, request):
        """Disable manual contributor creation."""
        return False


@admin.register(DetectionConfig)
class DetectionConfigAdmin(admin.ModelAdmin):
    """Admin interface for DetectionConfig model."""

    list_display = [
        'config_name', 'method', 'is_active', 'fundamental_freq_hz',
        'n_harmonics', 'confidence_threshold', 'created_at', 'created_by'
    ]
    list_filter = ['method', 'is_active', 'created_at']
    search_fields = ['config_name', 'created_by']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Identity', {
            'fields': ['config_name', 'is_active', 'method', 'created_by']
        }),
        ('Core Parameters', {
            'fields': [
                'fundamental_freq_hz', 'n_harmonics', 'confidence_threshold'
            ]
        }),
        ('Frequency Band', {
            'fields': ['freq_band_low_hz', 'freq_band_high_hz', 'harmonic_bandwidth_hz']
        }),
        ('SNR Parameters', {
            'fields': ['snr_min_db', 'snr_max_db', 'harmonic_min_snr_db']
        }),
        ('Evidence Weights', {
            'fields': ['weight_snr', 'weight_harmonic', 'weight_temporal', 'temporal_window']
        }),
        ('DOA & Framing', {
            'fields': ['mic_spacing_m', 'frame_length_ms', 'hop_length_ms']
        }),
        ('Audit', {
            'fields': ['created_at', 'updated_at']
        }),
    ]

    def save_model(self, request, obj, form, change):
        """Auto-set created_by on save."""
        if not change:  # Only on creation
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)
