"""API tests for IncidentForge REST endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from models.incident import Incident, IncidentSeverity, IncidentStatus

client = TestClient(app)


def _sample_incident() -> Incident:
    """Create a sample incident for testing."""
    return Incident(
        id="INC-TEST-001",
        title="Test API Latency Spike",
        description="Test incident for API testing",
        severity=IncidentSeverity.HIGH,
        affected_services=["test-api"],
        status=IncidentStatus.INVESTIGATING,
    )


def _sample_context() -> dict:
    """Create minimal context for testing."""
    return {
        "incident": {
            "id": "INC-TEST-001",
            "title": "Test API Latency Spike",
            "description": "Test incident for API testing",
            "severity": "high",
            "affected_services": ["test-api"],
            "status": "investigating",
        },
        "logs": [],
        "metrics": {},
        "traces": {},
    }


def test_create_investigation() -> None:
    """Test POST /investigations creates an investigation."""
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)

    assert response.status_code == 201
    data = response.json()
    assert "incident_id" in data
    assert data["incident_id"] == "INC-TEST-001"
    assert data["status"] == "complete"
    assert data["evidence_count"] >= 0
    assert data["findings_count"] >= 0
    assert data["recommendations_count"] >= 0


def test_list_investigations() -> None:
    """Test GET /investigations returns created investigations."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201

    # List investigations
    response = client.get("/api/v1/investigations")
    assert response.status_code == 200
    data = response.json()
    assert "investigations" in data
    assert len(data["investigations"]) >= 1
    assert data["investigations"][0]["incident_id"] == "INC-TEST-001"


def test_get_investigation() -> None:
    """Test GET /investigations/{id} returns investigation summary."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the investigation
    response = client.get(f"/api/v1/investigations/{investigation_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "INC-TEST-001"
    assert data["status"] == "complete"


def test_get_investigation_state() -> None:
    """Test GET /investigations/{id}/state returns full state."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the full state
    response = client.get(f"/api/v1/investigations/{investigation_id}/state")
    assert response.status_code == 200
    data = response.json()
    assert "incident" in data
    assert "status" in data
    assert "evidence" in data
    assert "findings" in data
    assert "hypotheses" in data
    assert "recommendations" in data
    assert "timeline" in data


def test_get_investigation_timeline() -> None:
    """Test GET /investigations/{id}/timeline works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the timeline
    response = client.get(f"/api/v1/investigations/{investigation_id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert "timeline" in data
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) > 0


def test_get_investigation_evidence() -> None:
    """Test GET /investigations/{id}/evidence works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the evidence
    response = client.get(f"/api/v1/investigations/{investigation_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert "evidence" in data
    assert isinstance(data["evidence"], list)


def test_get_investigation_findings() -> None:
    """Test GET /investigations/{id}/findings works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the findings
    response = client.get(f"/api/v1/investigations/{investigation_id}/findings")
    assert response.status_code == 200
    data = response.json()
    assert "findings" in data
    assert isinstance(data["findings"], list)


def test_get_investigation_recommendations() -> None:
    """Test GET /investigations/{id}/recommendations works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Get the recommendations
    response = client.get(f"/api/v1/investigations/{investigation_id}/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


def test_unknown_investigation_returns_404() -> None:
    """Test that unknown investigation ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    endpoints = [
        f"/api/v1/investigations/{fake_id}",
        f"/api/v1/investigations/{fake_id}/state",
        f"/api/v1/investigations/{fake_id}/timeline",
        f"/api/v1/investigations/{fake_id}/evidence",
        f"/api/v1/investigations/{fake_id}/findings",
        f"/api/v1/investigations/{fake_id}/recommendations",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 404, f"Endpoint {endpoint} should return 404"
        assert "not found" in response.json()["detail"].lower()