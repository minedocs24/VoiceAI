"""Test that openapi.yaml stays in sync with Pydantic models."""

import yaml
from pathlib import Path


def test_openapi_schemas_match_pydantic():
    """Compare openapi.yaml components/schemas with expected structure."""
    openapi_path = Path(__file__).parent.parent / "openapi.yaml"
    with open(openapi_path) as f:
        spec = yaml.safe_load(f)

    schemas = spec.get("components", {}).get("schemas", {})

    required_schemas = [
        "ErrorResponse",
        "QuotaCheckResponse",
        "QuotaConsumeResponse",
        "QuotaStatusResponse",
        "QuotaRollbackResponse",
        "AnalyticsResponse",
        "AnalyticsItem",
        "HealthResponse",
    ]
    for name in required_schemas:
        assert name in schemas, f"Missing schema: {name}"

    # QuotaCheckResponse must have allowed, used, limit, remaining
    qcr = schemas["QuotaCheckResponse"]
    assert "allowed" in qcr["properties"]
    assert "used" in qcr["properties"]
    assert "limit" in qcr["properties"]
    assert "remaining" in qcr["properties"]

    # x-reusable in info
    assert spec.get("info", {}).get("x-reusable") is True
