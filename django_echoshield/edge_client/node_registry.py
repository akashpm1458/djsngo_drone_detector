"""
Node Registry for tracking active edge nodes and their detections.

This is an in-memory registry that tracks:
- Active edge nodes (with GPS location and last seen time)
- Recent detections from each node
- Cleanup of stale nodes/detections based on retention policy
"""
import time
import math
from collections import defaultdict
from typing import Dict, List, Optional, Any
from django.conf import settings


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: First point coordinates (decimal degrees)
        lat2, lon2: Second point coordinates (decimal degrees)

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_bearing_from_coords(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing (azimuth) from point 1 to point 2.

    Args:
        lat1, lon1: Starting point (decimal degrees)
        lat2, lon2: Ending point (decimal degrees)

    Returns:
        Bearing in degrees (0-360, where 0 is North)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)

    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

    bearing_rad = math.atan2(x, y)
    bearing_deg = (math.degrees(bearing_rad) + 360) % 360

    return bearing_deg


class NodeRegistry:
    """
    In-memory registry for tracking active edge nodes and their detections.
    """

    def __init__(self, retention_seconds: int = 60):
        """
        Initialize the node registry.

        Args:
            retention_seconds: How long to keep nodes/detections before cleanup
        """
        self.retention_seconds = retention_seconds
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.detections: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def register_node(self, node_id: str, lat: float, lon: float, accuracy_m: float = 50.0):
        """
        Register or update a node in the registry.

        Args:
            node_id: Unique identifier for the node
            lat: Latitude (decimal degrees)
            lon: Longitude (decimal degrees)
            accuracy_m: GPS accuracy in meters
        """
        self.nodes[node_id] = {
            'node_id': node_id,
            'lat': lat,
            'lon': lon,
            'accuracy_m': accuracy_m or 50.0,
            'last_seen': time.time()
        }

    def add_detection(self, node_id: str, event_id: str, ts_ns: int, confidence: float,
                      lat: float, lon: float):
        """
        Add a detection to the registry.

        Args:
            node_id: Node that made the detection
            event_id: Unique event identifier
            ts_ns: Detection timestamp (nanoseconds)
            confidence: Detection confidence (0.0-1.0)
            lat: Detection latitude
            lon: Detection longitude
        """
        detection = {
            'event_id': event_id,
            'node_id': node_id,
            'ts_ns': ts_ns,
            'confidence': confidence,
            'timestamp': time.time(),
            'lat': lat,
            'lon': lon
        }
        self.detections[node_id].append(detection)
        self._cleanup()

    def get_nearby_nodes(self, node_id: str, max_radius_m: float = 100.0) -> List[Dict[str, Any]]:
        """
        Get all nodes within a certain radius of the specified node.

        Args:
            node_id: The reference node
            max_radius_m: Maximum radius in meters

        Returns:
            List of nearby node dictionaries with distance and bearing info
        """
        if node_id not in self.nodes:
            return []

        current_node = self.nodes[node_id]
        nearby = []

        for other_id, other_node in self.nodes.items():
            if other_id == node_id:
                continue

            distance_m = haversine_distance(
                current_node['lat'], current_node['lon'],
                other_node['lat'], other_node['lon']
            )

            if distance_m <= max_radius_m:
                bearing_to_node = calculate_bearing_from_coords(
                    current_node['lat'], current_node['lon'],
                    other_node['lat'], other_node['lon']
                )

                nearby.append({
                    **other_node,
                    'distance_m': distance_m,
                    'bearing_to_node': bearing_to_node
                })

        # Sort by distance (closest first)
        nearby.sort(key=lambda n: n['distance_m'])
        return nearby

    def find_concurrent_detections(self, ts_ns: int, time_window_ns: int = 5_000_000_000,
                                   min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Find detections from all nodes within a time window.

        Args:
            ts_ns: Reference timestamp (nanoseconds)
            time_window_ns: Time window in nanoseconds (default: 5 seconds)
            min_confidence: Minimum confidence threshold

        Returns:
            List of concurrent detections
        """
        concurrent = []

        for node_id, detections in self.detections.items():
            for det in detections:
                if (abs(det['ts_ns'] - ts_ns) <= time_window_ns and
                        det['confidence'] >= min_confidence):
                    concurrent.append(det)

        return concurrent

    def get_node_status(self) -> Dict[str, Any]:
        """
        Get registry status information.

        Returns:
            Dictionary with registry statistics
        """
        total_nodes = len(self.nodes)
        total_detections = sum(len(dets) for dets in self.detections.values())

        return {
            'total_nodes': total_nodes,
            'total_detections': total_detections,
            'nodes': list(self.nodes.keys()),
            'retention_seconds': self.retention_seconds
        }

    def _cleanup(self):
        """
        Remove stale nodes and detections based on retention policy.
        """
        current_time = time.time()
        cutoff_time = current_time - self.retention_seconds

        # Remove stale nodes
        stale_nodes = [
            node_id for node_id, node in self.nodes.items()
            if node['last_seen'] < cutoff_time
        ]
        for node_id in stale_nodes:
            del self.nodes[node_id]

        # Remove stale detections
        for node_id in list(self.detections.keys()):
            self.detections[node_id] = [
                det for det in self.detections[node_id]
                if det['timestamp'] >= cutoff_time
            ]
            # Remove empty detection lists
            if not self.detections[node_id]:
                del self.detections[node_id]


# Global registry instance
_registry: Optional[NodeRegistry] = None


def get_registry() -> NodeRegistry:
    """
    Get the global node registry instance (singleton pattern).

    Returns:
        The global NodeRegistry instance
    """
    global _registry
    if _registry is None:
        retention = settings.ECHOSHIELD.get('NODE_RETENTION_SECONDS', 60)
        _registry = NodeRegistry(retention_seconds=retention)
    return _registry


def find_nearby_nodes(lat: float, lon: float, all_nodes: List[Dict], max_radius_m: float) -> List[Dict]:
    """
    Helper function to find nearby nodes (used by GCC-PHAT algorithm).

    Args:
        lat, lon: Reference point
        all_nodes: List of all node dictionaries
        max_radius_m: Maximum radius in meters

    Returns:
        List of nearby nodes with distance and bearing
    """
    nearby = []

    for node in all_nodes:
        distance_m = haversine_distance(lat, lon, node['lat'], node['lon'])

        if distance_m <= max_radius_m:
            bearing_to_node = calculate_bearing_from_coords(lat, lon, node['lat'], node['lon'])
            nearby.append({
                **node,
                'distance_m': distance_m,
                'bearing_to_node': bearing_to_node
            })

    nearby.sort(key=lambda n: n['distance_m'])
    return nearby
