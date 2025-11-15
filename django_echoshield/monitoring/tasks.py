"""
Celery tasks for background processing.

Implements:
- Track aggregation (multi-node clustering)
- Event deduplication
- Expired track cleanup
"""
import logging
import math
from typing import List, Dict, Any
from collections import defaultdict
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from celery import shared_task

from core.models import Event, Track, TrackContributor

logger = logging.getLogger(__name__)


def angular_diff(angle1: float, angle2: float) -> float:
    """
    Calculate the circular distance between two angles.

    Args:
        angle1: First angle (degrees)
        angle2: Second angle (degrees)

    Returns:
        Minimum angular distance (0-180 degrees)
    """
    diff = abs(angle1 - angle2) % 360.0
    return min(diff, 360.0 - diff)


@shared_task
def deduplicate_events():
    """
    Mark duplicate events from the same node.

    Deduplication criteria:
    - Same sensor_node_id
    - Time delta <= 5 seconds
    - Bearing difference <= 20 degrees (circular)
    """
    logger.info("Starting event deduplication task")

    # Get configuration
    time_delta_ns = settings.ECHOSHIELD.get('DEDUP_TIME_DELTA_NS', 5_000_000_000)
    bearing_delta_deg = settings.ECHOSHIELD.get('DEDUP_BEARING_DELTA_DEG', 20.0)

    # Load recent events (last 10 minutes, not already marked as duplicates)
    ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
    events = list(Event.objects.filter(
        created_at__gte=ten_minutes_ago,
        duplicate_flag=False
    ).order_by('sensor_node_id', 'ts_ns'))

    duplicates = []

    # Check for duplicates
    for i, event_a in enumerate(events):
        for event_b in events[i+1:]:
            # Same node?
            if event_a.sensor_node_id != event_b.sensor_node_id:
                continue

            # Within time window?
            time_diff = abs(event_a.ts_ns - event_b.ts_ns)
            if time_diff > time_delta_ns:
                break  # Events are sorted by time, so we can break here

            # Similar bearing (if both have bearings)?
            if event_a.bearing_deg is not None and event_b.bearing_deg is not None:
                bearing_diff = angular_diff(event_a.bearing_deg, event_b.bearing_deg)
                if bearing_diff > bearing_delta_deg:
                    continue

            # Mark newer event as duplicate
            newer = event_a if event_a.ts_ns >= event_b.ts_ns else event_b
            duplicates.append(newer.id)
            logger.info(f"Marked event {newer.event_id} as duplicate")

    # Update duplicates in database
    if duplicates:
        Event.objects.filter(id__in=duplicates).update(
            duplicate_flag=True,
            validity_status='invalid'
        )
        logger.info(f"Deduplication complete: {len(duplicates)} duplicates marked")
    else:
        logger.info("Deduplication complete: no duplicates found")

    return len(duplicates)


@shared_task
def aggregate_tracks():
    """
    Aggregate bearing-only detections from multiple nodes into tracks.

    Clustering criteria:
    - Time window: 10 seconds
    - Minimum contributors: 2 distinct nodes
    - Averaging strategy: circular mean for bearings
    """
    logger.info("Starting track aggregation task")

    # Get configuration
    window_ns = settings.ECHOSHIELD.get('AGGREGATION_WINDOW_NS', 10_000_000_000)
    min_contributors = settings.ECHOSHIELD.get('MIN_TRACK_CONTRIBUTORS', 2)

    # Load recent bearing events (not duplicates, have bearing)
    recent_cutoff = timezone.now() - timezone.timedelta(minutes=5)
    bearing_events = Event.objects.filter(
        created_at__gte=recent_cutoff,
        duplicate_flag=False,
        bearing_deg__isnull=False,
        object_track_id__isnull=True  # Not yet assigned to a track
    ).order_by('ts_ns')

    if not bearing_events:
        logger.info("No events to aggregate")
        return 0

    # Cluster events by time buckets
    buckets = defaultdict(list)
    for event in bearing_events:
        bucket_key = event.ts_ns // window_ns
        buckets[bucket_key].append(event)

    tracks_created = 0

    # Process each bucket
    for bucket_key, events in buckets.items():
        # Check if we have enough distinct nodes
        distinct_nodes = {e.sensor_node_id for e in events}
        if len(distinct_nodes) < min_contributors:
            continue

        # Calculate aggregated bearing (circular mean)
        bearings = [e.bearing_deg for e in events if e.bearing_deg is not None]
        if not bearings:
            continue

        # Circular mean calculation
        sin_sum = sum(math.sin(math.radians(b)) for b in bearings)
        cos_sum = sum(math.cos(math.radians(b)) for b in bearings)
        aggregated_bearing = math.degrees(math.atan2(sin_sum, cos_sum))
        if aggregated_bearing < 0:
            aggregated_bearing += 360

        # Calculate confidence based on bearing variance
        bearing_std = calculate_circular_std(bearings)
        confidence = max(0.0, 1.0 - (bearing_std / 180.0))

        # Create or update track
        track_id = f"bearing-{bucket_key}"
        first_ts = min(e.ts_ns for e in events)
        last_ts = max(e.ts_ns for e in events)

        with transaction.atomic():
            track, created = Track.objects.update_or_create(
                track_id=track_id,
                defaults={
                    'method': 'bearing_only',
                    'first_ts_ns': first_ts,
                    'last_ts_ns': last_ts,
                    'aggregated_bearing_deg': aggregated_bearing,
                    'aggregation_conf': confidence,
                    'status': 'active'
                }
            )

            # Link events to track
            for event in events:
                event.object_track_id = track_id
                event.save(update_fields=['object_track_id'])

                # Create contributor record
                TrackContributor.objects.get_or_create(
                    track=track,
                    event=event,
                    defaults={
                        'sensor_node_id': event.sensor_node_id,
                        'bearing_deg': event.bearing_deg,
                        'ts_ns': event.ts_ns
                    }
                )

            if created:
                tracks_created += 1
                logger.info(f"Created track {track_id} with {len(events)} contributors")

    logger.info(f"Track aggregation complete: {tracks_created} tracks created")
    return tracks_created


@shared_task
def cleanup_expired_tracks():
    """
    Mark tracks as expired if they haven't been updated recently.

    A track is considered expired if:
    - Status is 'active'
    - Last update was more than 1 minute ago
    """
    logger.info("Starting expired track cleanup task")

    # Get cutoff time (1 minute ago)
    cutoff_ns = int((timezone.now().timestamp() - 60) * 1_000_000_000)

    # Find active tracks with old last_ts_ns
    expired = Track.objects.filter(
        status='active',
        last_ts_ns__lt=cutoff_ns
    ).update(status='expired')

    logger.info(f"Expired track cleanup complete: {expired} tracks marked as expired")
    return expired


def calculate_circular_std(angles: List[float]) -> float:
    """
    Calculate circular standard deviation of angles.

    Args:
        angles: List of angles in degrees

    Returns:
        Circular standard deviation in degrees
    """
    if not angles:
        return 0.0

    # Convert to radians and calculate
    angles_rad = [math.radians(a) for a in angles]
    sin_sum = sum(math.sin(a) for a in angles_rad)
    cos_sum = sum(math.cos(a) for a in angles_rad)

    n = len(angles)
    r = math.sqrt(sin_sum**2 + cos_sum**2) / n

    # Circular standard deviation
    if r < 1.0:
        s = math.sqrt(-2 * math.log(r))
        return math.degrees(s)
    else:
        return 0.0
