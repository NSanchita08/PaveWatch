"""Tests for STEP 16: Accessible route check (polyline proximity, routing service, view)."""

import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import Category, Ward
from reports.models import Report
from reports.routing import decode_polyline, reports_near_polyline, sample_polyline

User = get_user_model()


@pytest.mark.django_db
def test_reports_within_15m_of_handmade_polyline():
    ward = Ward.objects.create(name="Koramangala", zone="ZoneA", centroid_lat=12.9352, centroid_lon=77.6245)
    cat = Category.objects.create(name="Broken Pavement", sla_days=14, base_severity=3)
    reporter = User.objects.create_user(username="secret_reporter", email="secret@example.com", password="pw")

    # Hand-made straight line along lat=12.9352 from lon=77.6200 to lon=77.6220 (~217 m long)
    line = [(12.9352, 77.6200), (12.9352, 77.6220)]
    sampled = sample_polyline(line, step_m=10.0)
    assert len(sampled) >= 20

    # Report 5 m north of midpoint (~0.000045 deg lat) -> should be found
    near_open = Report.objects.create(
        reporter=reporter,
        category=cat,
        ward=ward,
        lat=12.935245,
        lon=77.6210,
        severity=2,
        status=Report.Status.SUBMITTED,
    )
    # Report 5 m north of midpoint, but CLOSED -> should NOT be found
    Report.objects.create(
        reporter=reporter,
        category=cat,
        ward=ward,
        lat=12.935245,
        lon=77.6211,
        severity=2,
        status=Report.Status.CLOSED,
    )
    # Report 80 m north of midpoint (~0.00072 deg lat) -> outside 15 m, should NOT be found
    Report.objects.create(
        reporter=reporter,
        category=cat,
        ward=ward,
        lat=12.93592,
        lon=77.6210,
        severity=2,
        status=Report.Status.SUBMITTED,
    )

    matches = reports_near_polyline(line, radius_m=15.0, step_m=10.0)
    assert len(matches) == 1
    assert matches[0]["id"] == near_open.pk
    assert matches[0]["distance_m"] <= 15.0
    # Ensure no reporter personal data is present
    serialized = json.dumps(matches)
    assert "secret_reporter" not in serialized
    assert "secret@example.com" not in serialized


def test_decode_polyline_known():
    # Standard Google polyline example: "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    pts = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert len(pts) == 3
    assert abs(pts[0][0] - 38.5) < 1e-4
    assert abs(pts[0][1] - (-120.2)) < 1e-4


@pytest.mark.django_db
def test_route_check_view_get_and_post(client):
    resp_get = client.get(reverse("route_check"))
    assert resp_get.status_code == 200
    assert b"Accessible" in resp_get.content

    with patch(
        "reports.routing.fetch_walking_route",
        return_value={
            "ok": True,
            "points": [(12.9352, 77.6200), (12.9352, 77.6220)],
            "distance_m": 220,
            "duration_s": 180,
            "provider": "google",
        },
    ):
        resp_post = client.post(
            reverse("route_check"),
            data=json.dumps({
                "start_lat": 12.9352,
                "start_lon": 77.6200,
                "end_lat": 12.9352,
                "end_lon": 77.6220,
            }),
            content_type="application/json",
        )
    assert resp_post.status_code == 200
    data = resp_post.json()
    assert data["ok"] is True
    assert data["distance_m"] == 220
    assert data["blockages"] == []


@pytest.mark.django_db
def test_api_geocode_returns_results_and_handles_failure(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
    with patch("requests.get", side_effect=RuntimeError("offline")):
        resp = client.get(reverse("api_geocode"), {"q": "Indiranagar"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    fake_resp = {
        "status": "OK",
        "results": [{
            "formatted_address": "Indiranagar, Bengaluru, Karnataka, India",
            "geometry": {"location": {"lat": 12.9784, "lng": 77.6408}},
        }],
    }
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = fake_resp
        mock_get.return_value.raise_for_status.return_value = None
        resp2 = client.get(reverse("api_geocode"), {"q": "Indiranagar"})
    assert resp2.status_code == 200
    assert len(resp2.json()["results"]) == 1
    assert resp2.json()["results"][0]["lat"] == 12.9784
