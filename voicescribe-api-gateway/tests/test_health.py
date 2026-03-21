"""Tests for health endpoint."""

def test_health(client):
    """Health returns 200."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_metrics(client):
    """Metrics returns 200."""
    r = client.get("/metrics")
    assert r.status_code == 200
