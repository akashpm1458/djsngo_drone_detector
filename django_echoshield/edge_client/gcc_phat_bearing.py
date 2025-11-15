"""
GCC-PHAT (Generalized Cross-Correlation with Phase Transform) Bearing Estimation.

This module implements Time Difference of Arrival (TDOA) based bearing estimation
using GCC-PHAT algorithm for multi-node acoustic detection.

Algorithm:
1. Calculate TDOA between two nodes from detection timestamps
2. Convert TDOA to distance difference using speed of sound
3. Use hyperbolic geometry to calculate bearing angle
4. Apply baseline geometry considerations for confidence
"""
import math
from typing import Dict, List, Optional, Any
from django.conf import settings
from .node_registry import haversine_distance, calculate_bearing_from_coords


def tdoa_to_bearing(tau: float, node1_lat: float, node1_lon: float,
                    node2_lat: float, node2_lon: float,
                    speed_of_sound: float = 343.0) -> tuple:
    """
    Convert Time Difference of Arrival (TDOA) to bearing using hyperbolic geometry.

    Args:
        tau: Time delay in seconds (positive if sound arrives at node2 first)
        node1_lat, node1_lon: First node coordinates
        node2_lat, node2_lon: Second node coordinates
        speed_of_sound: Speed of sound in m/s (default: 343 m/s at 20°C)

    Returns:
        Tuple of (bearing_deg, confidence)
    """
    # Calculate baseline distance and bearing between nodes
    baseline_distance = haversine_distance(node1_lat, node1_lon, node2_lat, node2_lon)
    baseline_bearing = calculate_bearing_from_coords(node1_lat, node1_lon, node2_lat, node2_lon)

    # Convert TDOA to distance difference
    distance_diff = tau * speed_of_sound

    # Check if distance difference is physically possible
    if abs(distance_diff) > baseline_distance:
        # Clamp to baseline distance
        distance_diff = math.copysign(baseline_distance * 0.95, distance_diff)

    # Calculate angle using hyperbolic geometry
    # cos(theta) = distance_diff / baseline_distance
    cos_theta = distance_diff / baseline_distance
    cos_theta = max(-1.0, min(1.0, cos_theta))  # Clamp to [-1, 1]

    theta_rad = math.acos(abs(cos_theta))
    theta_deg = math.degrees(theta_rad)

    # Determine bearing relative to baseline
    # If tau > 0, sound arrived at node2 first, source is on node2's side
    if distance_diff > 0:
        bearing_deg = (baseline_bearing + 90 - theta_deg) % 360
    else:
        bearing_deg = (baseline_bearing + 90 + theta_deg) % 360

    # Calculate confidence based on geometry
    # Better confidence when nodes are perpendicular to source direction
    # sin(theta) is high for perpendicular, low for collinear
    geometry_factor = abs(math.sin(theta_rad))

    # Base confidence adjusted by geometry (0.5 to 1.0)
    base_confidence = 0.6
    confidence = base_confidence * (0.5 + 0.5 * geometry_factor)

    return bearing_deg, confidence


def estimate_bearing_multi_node(current_node: Dict[str, Any],
                                nearby_nodes: List[Dict[str, Any]],
                                detection_ts_ns: int,
                                speed_of_sound: float = None) -> Optional[Dict[str, Any]]:
    """
    Estimate bearing using GCC-PHAT TDOA from multiple nearby nodes.

    Args:
        current_node: Dictionary with 'node_id', 'lat', 'lon', 'ts_ns'
        nearby_nodes: List of nearby node dictionaries with detection timestamps
        detection_ts_ns: Current detection timestamp (nanoseconds)
        speed_of_sound: Speed of sound in m/s (default from settings)

    Returns:
        Dictionary with bearing estimation results, or None if estimation fails
    """
    if not nearby_nodes:
        return None

    # Get speed of sound from settings
    if speed_of_sound is None:
        speed_of_sound = settings.ECHOSHIELD.get('SPEED_OF_SOUND', 343.0)

    # Select the closest paired node
    # In production, you might want to try multiple nodes and average results
    paired_node = min(nearby_nodes, key=lambda n: n.get('distance_m', float('inf')))

    # Get timestamps for TDOA calculation
    # In this implementation, we use the timestamp difference between nodes
    # In production, this would come from actual signal cross-correlation
    if 'ts_ns' not in paired_node:
        # If paired node doesn't have timestamp, we can't calculate TDOA
        return None

    # Calculate TDOA from timestamps
    tau_ns = paired_node['ts_ns'] - detection_ts_ns
    tau = tau_ns / 1e9  # Convert to seconds

    # Estimate bearing
    bearing_deg, bearing_confidence = tdoa_to_bearing(
        tau,
        current_node['lat'], current_node['lon'],
        paired_node['lat'], paired_node['lon'],
        speed_of_sound
    )

    # Build result
    result = {
        'bearing_deg': bearing_deg,
        'bearing_confidence': bearing_confidence,
        'method': 'GCC_PHAT_TDOA',
        'paired_node_id': paired_node['node_id'],
        'baseline_distance_m': paired_node['distance_m'],
        'tdoa_sec': tau,
        'baseline_bearing_deg': paired_node['bearing_to_node']
    }

    return result


def gcc_phat_cross_correlation(signal1, signal2, fs):
    """
    Perform GCC-PHAT cross-correlation on two audio signals.

    This is a placeholder for actual signal processing implementation.
    In production, this would use NumPy/SciPy for FFT-based correlation.

    Args:
        signal1: First audio signal (numpy array)
        signal2: Second audio signal (numpy array)
        fs: Sampling frequency (Hz)

    Returns:
        Tuple of (tau, confidence) where tau is time delay in seconds
    """
    # This is a placeholder - in production you would implement:
    # 1. FFT of both signals
    # 2. Cross-power spectrum with Phase Transform
    # 3. IFFT to get correlation
    # 4. Find peak and convert to time delay

    # For now, we use timestamp-based TDOA (simpler for browser-based deployment)
    raise NotImplementedError(
        "Full GCC-PHAT signal processing not implemented. "
        "Using timestamp-based TDOA instead."
    )


def calculate_triangulated_position(bearings: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """
    Calculate triangulated position from multiple bearing measurements.

    This requires at least 2 bearings from different nodes.

    Args:
        bearings: List of bearing dictionaries with 'lat', 'lon', 'bearing_deg'

    Returns:
        Dictionary with 'lat', 'lon', 'confidence' or None
    """
    if len(bearings) < 2:
        return None

    # Triangulation implementation would go here
    # This is a placeholder for future enhancement
    # See: https://en.wikipedia.org/wiki/Triangulation_(surveying)

    # For MVP, we return None and rely on bearing-only tracks
    return None
