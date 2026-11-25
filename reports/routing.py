"""Accessible walking route check using Google Directions API or OpenRouteService."""

import os
from typing import Iterable

import requests

from .geo import bbox, haversine_m
from .models import Report


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google-encoded polyline string into a list of (lat, lon) tuples."""
    points: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        for coord_idx in range(2):
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if coord_idx == 0:
                lat += delta
            else:
                lng += delta
        points.append((lat / 1e5, lng / 1e5))

    return points


def sample_polyline(
    points: Iterable[tuple[float, float]], step_m: float = 10.0
) -> list[tuple[float, float]]:
    """Sample points along a polyline roughly every `step_m` meters."""
    pts = list(points)
    if len(pts) <= 1:
        return pts

    sampled: list[tuple[float, float]] = [pts[0]]
    for i in range(len(pts) - 1):
        lat1, lon1 = pts[i]
        lat2, lon2 = pts[i + 1]
        seg_len = haversine_m(lat1, lon1, lat2, lon2)
        if seg_len <= 0:
            continue
        steps = max(1, int(seg_len // step_m))
        for s in range(1, steps + 1):
            frac = s / steps
            sampled.append((
                lat1 + (lat2 - lat1) * frac,
                lon1 + (lon2 - lon1) * frac,
            ))
    return sampled


def reports_near_polyline(
    points: list[tuple[float, float]],
    radius_m: float = 15.0,
    step_m: float = 10.0,
) -> list[dict]:
    """
    Return open reports within `radius_m` meters of any sampled point along `points`.
    Contains no reporter personal data.
    """
    if not points:
        return []

    sampled = sample_polyline(points, step_m=step_m)
    lats = [p[0] for p in sampled]
    lons = [p[1] for p in sampled]
    lat_min, _, lon_min, _ = bbox(min(lats), min(lons), radius_m)
    _, lat_max, _, lon_max = bbox(max(lats), max(lons), radius_m)

    candidates = (
        Report.objects.filter(
            status__in=Report.OPEN_STATUSES,
            lat__range=(lat_min, lat_max),
            lon__range=(lon_min, lon_max),
        )
        .select_related("category", "ward")
    )

    matches: list[dict] = []
    for report in candidates:
        min_dist = min(
            haversine_m(report.lat, report.lon, s_lat, s_lon)
            for s_lat, s_lon in sampled
        )
        if min_dist <= radius_m:
            matches.append({
                "id": report.pk,
                "tracking_id": report.tracking_id or f"Report #{report.pk}",
                "category": report.category.name if report.category else "",
                "severity": report.severity,
                "status": report.status,
                "landmark": report.landmark,
                "lat": report.lat,
                "lon": report.lon,
                "distance_m": round(min_dist, 1),
                "detail_url": f"/r/{report.pk}/",
            })

    matches.sort(key=lambda item: item["distance_m"])
    return matches


def _fetch_google_walking(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float, api_key: str
) -> dict:
    """Call Google Routes API v2 (computeRoutes) for WALK mode."""
    resp = requests.post(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
        },
        json={
            "origin": {"location": {"latLng": {"latitude": start_lat, "longitude": start_lon}}},
            "destination": {"location": {"latLng": {"latitude": end_lat, "longitude": end_lon}}},
            "travelMode": "WALK",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    routes = data.get("routes") or []
    if not routes:
        err_msg = ((data.get("error") or {}).get("message")) or "No walking route found."
        return {"ok": False, "error": f"Routes API error: {err_msg}"}

    route = routes[0]
    enc = (route.get("polyline") or {}).get("encodedPolyline", "")
    points = decode_polyline(enc) if enc else []
    if not points:
        return {"ok": False, "error": "Route geometry was empty."}

    raw_dur = str(route.get("duration") or "").rstrip("s")
    duration_s = int(float(raw_dur)) if raw_dur else None

    return {
        "ok": True,
        "points": points,
        "distance_m": route.get("distanceMeters"),
        "duration_s": duration_s,
        "provider": "google",
    }


def _fetch_ors_walking(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float, api_key: str
) -> dict:
    resp = requests.post(
        "https://api.openrouteservice.org/v2/directions/foot-walking/geojson",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json={"coordinates": [[start_lon, start_lat], [end_lon, end_lat]]},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features") or []
    if not features:
        return {"ok": False, "error": "No walking route returned by OpenRouteService."}

    coords = (features[0].get("geometry") or {}).get("coordinates") or []
    points = [(float(lat), float(lon)) for lon, lat in coords]
    if not points:
        return {"ok": False, "error": "Route geometry was empty."}

    summary = ((features[0].get("properties") or {}).get("summary")) or {}
    return {
        "ok": True,
        "points": points,
        "distance_m": summary.get("distance"),
        "duration_s": summary.get("duration"),
        "provider": "ors",
    }


def fetch_walking_route(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> dict:
    """
    Fetch a walking route from Google Maps Directions API (if GOOGLE_MAPS_API_KEY is set)
    or OpenRouteService (if ORS_API_KEY is set). Never raises; returns {ok, ...}.
    """
    google_key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    ors_key = (os.getenv("ORS_API_KEY") or "").strip()

    if not google_key and not ors_key:
        return {
            "ok": False,
            "error": "Routing service is not configured. Please add GOOGLE_MAPS_API_KEY or ORS_API_KEY.",
        }

    try:
        if google_key:
            result = _fetch_google_walking(start_lat, start_lon, end_lat, end_lon, google_key)
            if result.get("ok") or not ors_key:
                return result
        return _fetch_ors_walking(start_lat, start_lon, end_lat, end_lon, ors_key)
    except Exception:
        return {
            "ok": False,
            "error": "Could not reach the routing service right now. Please try again shortly.",
        }
