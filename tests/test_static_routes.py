"""Test static file serving routes."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_serve_index():
    """Test homepage serves correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert b"Portfolio" in response.content


def test_serve_index_html():
    """Test homepage at /index.html serves correctly."""
    response = client.get("/index.html")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert b"Portfolio" in response.content


def test_serve_journey():
    """Test journey page serves correctly."""
    response = client.get("/journey.html")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_serve_finance():
    """Test finance page serves correctly."""
    response = client.get("/finance.html")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert b"Finance Overview" in response.content


def test_static_js_file():
    """Test JavaScript file accessible."""
    response = client.get("/assets/js/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"].lower()


def test_static_finance_js():
    """Test finance.js accessible."""
    response = client.get("/assets/js/finance.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"].lower()


def test_static_image():
    """Test image file accessible."""
    response = client.get("/assets/images/sonbip.png")
    assert response.status_code == 200
    assert "image/png" in response.headers["content-type"]


def test_static_json_data():
    """Test JSON data file accessible."""
    response = client.get("/data/journey.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_404_for_missing_file():
    """Test 404 returned for non-existent static file."""
    response = client.get("/nonexistent.html")
    assert response.status_code == 404


def test_health_endpoint_still_works():
    """Ensure existing /health endpoint still works."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
