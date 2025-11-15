"""
Mappers module for converting edge detection payloads to WirePacket format.

This module handles the transformation of browser-based detection events
into the compact WirePacket wire protocol format.
"""
import uuid
from typing import Dict, Any, Optional
from django.conf import settings
from .node_registry import get_registry
from .gcc_phat_bearing import estimate_bearing_multi_node


def to_wirepacket(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert edge detection payload to WirePacket format.

    Args:
        payload: Edge detection payload from browser
            {
                "nodeId": "NODE_IPHONE_01",
                "time_ms": 1699999999999,
                "azimuth_deg": 45.0,
                "confidence": 0.87,
                "event": "drone",
                "lat": 52.5163,
                "lon": 13.3777,
                "acc_m": 15.0
            }

    Returns:
        WirePacket dictionary ready for ingestion
    """
    # Extract detection data
    event_id = str(uuid.uuid4())
    ts_ns = int(payload.get("time_ms", 0)) * 1_000_000  # Convert ms to ns
    node_id = payload.get("nodeId", "NODE_UNKNOWN")
    bearing_deg = payload.get("azimuth_deg")
    confidence = float(payload.get("confidence", 0.0))

    # GPS location from browser geolocation API
    lat = payload.get("lat")
    lon = payload.get("lon")
    acc_m = payload.get("acc_m", 200.0)

    # Initialize variables
    gcc_phat_result = None
    location_method = "LOC_BEARING_ONLY"

    # Register node and detection in registry
    registry = get_registry()
    if lat is not None and lon is not None:
        registry.register_node(node_id, lat, lon, acc_m)
        registry.add_detection(node_id, event_id, ts_ns, confidence, lat, lon)

        # Try GCC-PHAT bearing estimation with nearby nodes
        max_radius_m = settings.ECHOSHIELD.get('GCC_PHAT_MAX_RADIUS_M', 100.0)
        nearby_nodes = registry.get_nearby_nodes(node_id, max_radius_m=max_radius_m)

        if nearby_nodes:
            # Find concurrent detections from nearby nodes
            time_window_ns = settings.ECHOSHIELD.get('GCC_PHAT_TIME_WINDOW_NS', 5_000_000_000)
            concurrent = registry.find_concurrent_detections(
                ts_ns,
                time_window_ns=time_window_ns,
                min_confidence=0.5
            )

            # Add timing info to nearby nodes
            for node in nearby_nodes:
                matching_det = next(
                    (det for det in concurrent if det['node_id'] == node['node_id']),
                    None
                )
                if matching_det:
                    node['ts_ns'] = matching_det['ts_ns']

            # Filter nearby nodes that have timing info
            nearby_with_timing = [n for n in nearby_nodes if 'ts_ns' in n]

            if nearby_with_timing:
                # Estimate bearing using GCC-PHAT TDOA
                gcc_phat_result = estimate_bearing_multi_node(
                    current_node={'node_id': node_id, 'lat': lat, 'lon': lon, 'ts_ns': ts_ns},
                    nearby_nodes=nearby_with_timing,
                    detection_ts_ns=ts_ns
                )

                if gcc_phat_result:
                    bearing_deg = gcc_phat_result['bearing_deg']
                    location_method = "LOC_ACOUSTIC_TRIANGULATION"

    # Build WirePacket
    wire_packet = {
        "event_id": event_id,
        "sensor_type": "acoustic",
        "ts_ns": ts_ns,
        "sensor_node_id": node_id,
        "location": {
            "lat_int": int(lat * 1e5) if lat is not None else 0,
            "lon_int": int(lon * 1e5) if lon is not None else 0,
            "error_radius_m": int(acc_m)
        },
        "bearing_deg": int(bearing_deg * 100) if bearing_deg is not None else None,
        "bearing_confidence": int(confidence * 100),
        "n_objects_detected": 1,
        "event_code": 10,  # Event code 10 = drone detection
        "location_method": location_method,
        "packet_version": 1
    }

    # Add GCC-PHAT metadata if available
    if gcc_phat_result:
        wire_packet["gcc_phat_metadata"] = {
            "method": gcc_phat_result['method'],
            "paired_node_id": gcc_phat_result['paired_node_id'],
            "baseline_distance_m": gcc_phat_result['baseline_distance_m'],
            "tdoa_sec": gcc_phat_result['tdoa_sec'],
            "baseline_bearing_deg": gcc_phat_result['baseline_bearing_deg']
        }

    return wire_packet


def wirepacket_to_dict(wire_packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert WirePacket to a dictionary suitable for logging or display.

    Args:
        wire_packet: WirePacket dictionary

    Returns:
        Human-readable dictionary
    """
    result = {
        'event_id': wire_packet['event_id'],
        'sensor_type': wire_packet['sensor_type'],
        'sensor_node_id': wire_packet['sensor_node_id'],
        'timestamp_ns': wire_packet['ts_ns'],
        'location': {
            'lat': wire_packet['location']['lat_int'] / 1e5,
            'lon': wire_packet['location']['lon_int'] / 1e5,
            'accuracy_m': wire_packet['location']['error_radius_m']
        },
        'bearing_deg': wire_packet['bearing_deg'] / 100.0 if wire_packet.get('bearing_deg') else None,
        'confidence': wire_packet['bearing_confidence'] / 100.0,
        'n_objects': wire_packet['n_objects_detected'],
        'event_code': wire_packet['event_code'],
        'location_method': wire_packet['location_method'],
        'version': wire_packet['packet_version']
    }

    if 'gcc_phat_metadata' in wire_packet:
        result['gcc_phat'] = wire_packet['gcc_phat_metadata']

    return result
