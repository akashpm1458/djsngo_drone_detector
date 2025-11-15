"""
Wire Codec module for converting between WirePacket and Canonical Event formats.

WirePacket: Compact wire protocol format (uses fixed-point integers)
Canonical Event: Human-readable format (uses floats) stored in database
"""
import time
from typing import Dict, Any
from django.conf import settings


def get_current_time_ns() -> int:
    """
    Get current time in nanoseconds.

    Returns:
        Current timestamp in nanoseconds
    """
    return int(time.time() * 1_000_000_000)


def calculate_latency_status(latency_ns: int) -> str:
    """
    Calculate latency status based on thresholds.

    Args:
        latency_ns: Latency in nanoseconds

    Returns:
        'normal', 'delayed', or 'obsolete'
    """
    normal_threshold = settings.ECHOSHIELD.get('LATENCY_NORMAL_NS', 500_000_000)
    delayed_threshold = settings.ECHOSHIELD.get('LATENCY_DELAYED_NS', 2_000_000_000)

    if latency_ns <= normal_threshold:
        return 'normal'
    elif latency_ns <= delayed_threshold:
        return 'delayed'
    else:
        return 'obsolete'


def to_canonical(wire_packet: Dict[str, Any], rx_ns: int = None) -> Dict[str, Any]:
    """
    Convert WirePacket to Canonical Event format.

    Args:
        wire_packet: WirePacket dictionary
        rx_ns: Server receipt timestamp (nanoseconds). If None, uses current time.

    Returns:
        Canonical Event dictionary
    """
    if rx_ns is None:
        rx_ns = get_current_time_ns()

    # Extract wire packet fields
    ts_ns = wire_packet['ts_ns']
    location = wire_packet['location']

    # Convert fixed-point integers to floats
    lat = location['lat_int'] / 1e5 if location.get('lat_int') else None
    lon = location['lon_int'] / 1e5 if location.get('lon_int') else None
    error_radius_m = float(location.get('error_radius_m', 0))

    # Convert bearing from int*100 to float
    bearing_deg = wire_packet.get('bearing_deg')
    if bearing_deg is not None:
        bearing_deg = bearing_deg / 100.0

    # Convert confidence from int (0-100) to float (0.0-1.0)
    bearing_conf = wire_packet.get('bearing_confidence', 0) / 100.0

    # Calculate latency
    latency_ns = max(0, rx_ns - ts_ns)
    latency_status = calculate_latency_status(latency_ns)

    # Build canonical event
    canonical = {
        # Core identity
        'event_id': wire_packet['event_id'],
        'sensor_type': wire_packet['sensor_type'],
        'sensor_node_id': wire_packet['sensor_node_id'],

        # Timestamps
        'ts_ns': ts_ns,
        'rx_ns': rx_ns,
        'latency_ns': latency_ns,
        'latency_status': latency_status,

        # Location (converted)
        'lat': lat,
        'lon': lon,
        'error_radius_m': error_radius_m,

        # Bearing (converted)
        'bearing_deg': bearing_deg,
        'bearing_conf': bearing_conf,

        # Detection details
        'n_objects': wire_packet.get('n_objects_detected'),
        'event_code': str(wire_packet.get('event_code', '')),
        'location_method': wire_packet.get('location_method'),
        'packet_version': wire_packet.get('packet_version', 1),

        # Post-processing (defaults)
        'validity_status': 'unknown',
        'duplicate_flag': False,

        # GCC-PHAT metadata (if present)
        'gcc_phat_metadata': wire_packet.get('gcc_phat_metadata'),

        # Raw wire packet for audit
        'raw_wire_json': wire_packet
    }

    return canonical


def to_wire_packet(canonical: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Canonical Event back to WirePacket format.

    This is useful for re-transmission or testing.

    Args:
        canonical: Canonical Event dictionary

    Returns:
        WirePacket dictionary
    """
    # Convert floats to fixed-point integers
    lat_int = int(canonical.get('lat', 0) * 1e5)
    lon_int = int(canonical.get('lon', 0) * 1e5)
    error_radius_m = int(canonical.get('error_radius_m', 0))

    # Convert bearing to int*100
    bearing_deg = canonical.get('bearing_deg')
    if bearing_deg is not None:
        bearing_deg = int(bearing_deg * 100)

    # Convert confidence to int (0-100)
    bearing_conf = int(canonical.get('bearing_conf', 0) * 100)

    # Build wire packet
    wire_packet = {
        'event_id': canonical['event_id'],
        'sensor_type': canonical['sensor_type'],
        'ts_ns': canonical['ts_ns'],
        'sensor_node_id': canonical['sensor_node_id'],
        'location': {
            'lat_int': lat_int,
            'lon_int': lon_int,
            'error_radius_m': error_radius_m
        },
        'bearing_deg': bearing_deg,
        'bearing_confidence': bearing_conf,
        'n_objects_detected': canonical.get('n_objects', 1),
        'event_code': int(canonical.get('event_code', 0)),
        'location_method': canonical.get('location_method'),
        'packet_version': canonical.get('packet_version', 1)
    }

    # Add GCC-PHAT metadata if present
    if canonical.get('gcc_phat_metadata'):
        wire_packet['gcc_phat_metadata'] = canonical['gcc_phat_metadata']

    return wire_packet
