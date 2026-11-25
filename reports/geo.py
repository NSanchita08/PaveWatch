from math import radians, sin, cos, asin, sqrt

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance in meters between two lat/lon points."""
    R = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(a))

def bbox(lat: float, lon: float, meters: float):
    """Return (lat_min, lat_max, lon_min, lon_max) around a point for DB prefiltering."""
    dlat = meters / 111_000.0
    dlon = meters / (111_000.0 * max(cos(radians(lat)), 0.01))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon

def nearest_ward(lat: float, lon: float):
    """Return the closest Ward model instance to the given lat/lon."""
    from core.models import Ward
    best, best_d = None, float("inf")
    for w in Ward.objects.all():
        d = haversine_m(lat, lon, w.centroid_lat, w.centroid_lon)
        if d < best_d:
            best, best_d = w, d
    return best
