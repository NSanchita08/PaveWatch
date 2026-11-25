"""Tests for STEP 15: Optional AI photo assistant (/api/suggest/ and report_create)."""

import io
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from core.models import Category, Ward
from reports.ai import suggest_from_image
from reports.models import Report

User = get_user_model()


def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(200, 100, 50)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.django_db
def test_api_suggest_returns_null_when_ai_disabled(client, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "False")
    user = User.objects.create_user(username="ai_citizen", password="pw", role=User.Role.CITIZEN)
    client.force_login(user)

    img = SimpleUploadedFile("test.jpg", _make_jpeg_bytes(), content_type="image/jpeg")
    resp = client.post(reverse("api_suggest"), {"image": img})
    assert resp.status_code == 200
    assert resp.json() == {"suggestion": None}


@pytest.mark.django_db
def test_report_submission_works_with_ai_disabled(client, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "False")
    Ward.objects.create(name="Koramangala", zone="ZoneA", centroid_lat=12.9352, centroid_lon=77.6245)
    cat = Category.objects.create(name="Broken Pavement", sla_days=14, base_severity=3)
    user = User.objects.create_user(username="submitter_ai", password="pw", role=User.Role.CITIZEN)
    client.force_login(user)

    img = SimpleUploadedFile("test.jpg", _make_jpeg_bytes(), content_type="image/jpeg")
    resp = client.post(
        reverse("report_create"),
        {
            "category": cat.pk,
            "description": "Broken slab",
            "landmark": "Main Rd",
            "severity": 2,
            "lat": 12.9352,
            "lon": 77.6245,
            "photos": img,
        },
    )
    assert resp.status_code == 302
    report = Report.objects.get(reporter=user)
    assert report.ai_label == ""
    assert report.ai_confidence is None


@pytest.mark.django_db
def test_api_suggest_and_store_ai_fields_when_enabled(client, monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "True")
    Ward.objects.create(name="Indiranagar", zone="ZoneA", centroid_lat=12.9784, centroid_lon=77.6408)
    cat = Category.objects.create(name="Illegal Parking", sla_days=2, base_severity=1)
    user = User.objects.create_user(username="ai_user2", password="pw", role=User.Role.CITIZEN)
    client.force_login(user)

    fake_json = json.dumps({
        "is_obstruction": True,
        "category": "Illegal Parking",
        "severity": 3,
        "confidence": 0.91,
    })
    fake_msg = SimpleNamespace(content=[SimpleNamespace(type="text", text=fake_json)])

    with patch("anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = fake_msg
        img = SimpleUploadedFile("park.jpg", _make_jpeg_bytes(), content_type="image/jpeg")
        resp = client.post(reverse("api_suggest"), {"image": img})

    assert resp.status_code == 200
    payload = resp.json()["suggestion"]
    assert payload["category"] == "Illegal Parking"
    assert payload["category_id"] == cat.pk
    assert payload["severity"] == 3
    assert payload["confidence"] == 0.91

    # Submitting with ai_label and ai_confidence stores them and boosts trust_score by +20
    img2 = SimpleUploadedFile("park2.jpg", _make_jpeg_bytes(), content_type="image/jpeg")
    resp2 = client.post(
        reverse("report_create"),
        {
            "category": cat.pk,
            "description": "Car on footpath",
            "landmark": "100ft Rd",
            "severity": 3,
            "lat": 12.9784,
            "lon": 77.6408,
            "ai_label": "Illegal Parking",
            "ai_confidence": "0.91",
            "photos": img2,
        },
    )
    assert resp2.status_code == 302
    report = Report.objects.get(reporter=user)
    assert report.ai_label == "Illegal Parking"
    assert report.ai_confidence == 0.91
    assert report.trust_score >= 20


@pytest.mark.django_db
def test_suggest_from_image_fails_safe_on_exception(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "True")
    Category.objects.create(name="Broken Pavement", sla_days=14, base_severity=3)
    with patch("anthropic.Anthropic", side_effect=RuntimeError("API down")):
        assert suggest_from_image(_make_jpeg_bytes()) is None
