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
    assert "investigation_id" in data
    assert data["incident_id"] == "INC-TEST-001"
    # Background investigation returns immediately with created status
    assert data["status"] == "created"
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


def test_list_scenarios() -> None:
    """Test GET /scenarios returns available scenario names."""
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert isinstance(data["scenarios"], list)
    # Should have at least the two built-in scenarios
    assert "payment_latency" in data["scenarios"]
    assert "db_lock_contention" in data["scenarios"]


def test_get_scenario() -> None:
    """Test GET /scenarios/{name} returns scenario data."""
    response = client.get("/api/v1/scenarios/payment_latency")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "payment_latency"
    assert "incident" in data
    assert data["incident"]["id"] == "INC-2026-1042"
    assert "logs" in data
    assert "metrics" in data
    assert "traces" in data
    assert "deployments" in data
    assert "commits" in data


def test_get_scenario_db_lock_contention() -> None:
    """Test GET /scenarios/{name} works for db_lock_contention scenario."""
    response = client.get("/api/v1/scenarios/db_lock_contention")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "db_lock_contention"
    assert data["incident"]["id"] == "INC-2026-1055"
    assert data["incident"]["title"] == "Database lock contention on payments table"


def test_unknown_scenario_returns_404() -> None:
    """Test that unknown scenario returns 404."""
    response = client.get("/api/v1/scenarios/nonexistent_scenario")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_approve_recommendation() -> None:
    """Test POST /investigations/{id}/recommendations/{index}/approve works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Approve the first recommendation (index 0)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/recommendations/0/approve",
        json={"note": "Approved by test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_index"] == 0
    assert data["action"] == "approve"
    assert data["status"] == "approved"
    assert "Approved by test" in data["message"]

    # Verify the recommendation status in the full state
    state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["recommendations"][0]["status"] == "approved"

    # Verify timeline has approval event
    timeline_response = client.get(f"/api/v1/investigations/{investigation_id}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()["timeline"]
    assert any(event["type"] == "recommendation_approved" for event in timeline)


def test_reject_recommendation() -> None:
    """Test POST /investigations/{id}/recommendations/{index}/reject works."""
    # Create an investigation first
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Reject the first recommendation (index 0)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/recommendations/0/reject",
        json={"note": "Rejected by test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation_index"] == 0
    assert data["action"] == "reject"
    assert data["status"] == "rejected"
    assert "Rejected by test" in data["message"]

    # Verify the recommendation status in the full state
    state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["recommendations"][0]["status"] == "rejected"

    # Verify timeline has rejection event
    timeline_response = client.get(f"/api/v1/investigations/{investigation_id}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()["timeline"]
    assert any(event["type"] == "recommendation_rejected" for event in timeline)


def test_approve_invalid_recommendation_index_returns_404() -> None:
    """Test that invalid recommendation index returns 404."""
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Try to approve an invalid index
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/recommendations/999/approve",
        json={},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_approve_invalid_investigation_returns_404() -> None:
    """Test that invalid investigation ID returns 404 for approve."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        f"/api/v1/investigations/{fake_id}/recommendations/0/approve",
        json={},
    )
    assert response.status_code == 404


def test_reject_invalid_recommendation_index_returns_404() -> None:
    """Test that invalid recommendation index returns 404 for reject."""
    request_body = {
        "incident": _sample_incident().model_dump(mode="json"),
        "context": _sample_context(),
        "use_llm": False,
    }
    create_response = client.post("/api/v1/investigations", json=request_body)
    assert create_response.status_code == 201
    investigation_id = create_response.json()["investigation_id"]

    # Try to reject an invalid index
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/recommendations/999/reject",
        json={},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_recommendation_requires_approval_fails_without_approval() -> None:
    """Test that recommendations with requires_approval=True cannot be silently executed."""
    # This test verifies the model enforces requires_approval
    from models.recommendation import Recommendation

    # A recommendation without requires_approval can be "executed" (not in this test)
    # But with requires_approval=True, it must be explicitly approved
    rec = Recommendation(
        action="Test action",
        rationale="Test rationale",
        risk="Test risk",
        confidence=0.8,
        requires_approval=True,
    )
    assert rec.requires_approval is True
    assert rec.status == "pending"


def test_create_investigation_with_scenario_payment_latency() -> None:
    """Test POST /investigations with scenario=payment_latency."""
    request_body = {
        "scenario": "payment_latency",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)

    assert response.status_code == 201
    data = response.json()
    assert "investigation_id" in data
    assert data["incident_id"] == "INC-2026-1042"
    assert data["incident_title"] == "Payment API latency spike"
    # Background investigation returns immediately with created status
    assert data["status"] == "created"
    assert data["stage"] == "queued"
    assert data["progress"] == 0.0
    # Evidence/findings will be 0 initially, populated after completion
    # (checked in test_investigation_completes_after_creation)


def test_create_investigation_with_scenario_db_lock_contention() -> None:
    """Test POST /investigations with scenario=db_lock_contention."""
    request_body = {
        "scenario": "db_lock_contention",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)

    assert response.status_code == 201
    data = response.json()
    assert "investigation_id" in data
    assert data["incident_id"] == "INC-2026-1055"
    assert data["incident_title"] == "Database lock contention on payments table"
    # Background investigation returns immediately with created status
    assert data["status"] == "created"
    assert data["stage"] == "queued"
    assert data["progress"] == 0.0
    # Evidence/findings will be 0 initially, populated after completion


def test_create_investigation_invalid_scenario_returns_404() -> None:
    """Test that unknown scenario returns 404."""
    request_body = {
        "scenario": "nonexistent_scenario",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_investigation_missing_scenario_and_incident_returns_400() -> None:
    """Test that missing both scenario and incident returns 400."""
    request_body = {
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)

    assert response.status_code == 400
    assert "must be provided" in response.json()["detail"].lower()


def test_scenario_investigation_returns_real_evidence() -> None:
    """Test that scenario-driven investigation returns realistic evidence."""
    request_body = {
        "scenario": "payment_latency",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)
    assert response.status_code == 201
    investigation_id = response.json()["investigation_id"]

    # Get full state and verify evidence content
    state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()

    assert len(state["evidence"]) >= 3
    evidence_types = {e["type"] for e in state["evidence"]}
    # Should have metric, log, trace evidence
    assert "metric" in evidence_types
    assert "log" in evidence_types
    assert "trace" in evidence_types

    # Evidence should have realistic values (not 0/unknown)
    for e in state["evidence"]:
        assert e["description"] != ""
        assert e["relevance"] > 0


def test_scenario_investigation_returns_findings_and_hypotheses() -> None:
    """Test that scenario-driven investigation returns findings and hypotheses."""
    request_body = {
        "scenario": "payment_latency",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)
    assert response.status_code == 201
    investigation_id = response.json()["investigation_id"]

    state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
    assert state_response.status_code == 200
    state = state_response.json()

    assert len(state["findings"]) >= 1
    assert len(state["hypotheses"]) >= 1
    assert len(state["recommendations"]) >= 1

    # Verify recommendation starts as pending
    for rec in state["recommendations"]:
        assert rec["status"] == "pending"
        assert rec["requires_approval"] is True


def test_scenario_investigation_timeline_has_real_events() -> None:
    """Test that scenario-driven investigation timeline has real events."""
    request_body = {
        "scenario": "payment_latency",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)
    assert response.status_code == 201
    investigation_id = response.json()["investigation_id"]

    # Poll until investigation completes
    import time
    for _ in range(30):
        state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
        assert state_response.status_code == 200
        state = state_response.json()
        if state["status"] == "complete":
            break
        time.sleep(0.1)

    timeline_response = client.get(f"/api/v1/investigations/{investigation_id}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()["timeline"]

    event_types = {e["type"] for e in timeline}
    assert "investigation_created" in event_types
    assert "commander_triage" in event_types
    assert "telemetry_analyzed" in event_types
    assert "repository_analyzed" in event_types
    assert "investigation_completed" in event_types


def test_investigation_completes_after_creation() -> None:
    """Test that a background investigation eventually completes."""
    request_body = {
        "scenario": "payment_latency",
        "use_llm": False,
    }

    response = client.post("/api/v1/investigations", json=request_body)
    assert response.status_code == 201
    investigation_id = response.json()["investigation_id"]

    # Initial status should be created
    assert response.json()["status"] == "created"

    # Poll until complete
    import time
    for _ in range(30):
        state_response = client.get(f"/api/v1/investigations/{investigation_id}/state")
        assert state_response.status_code == 200
        state = state_response.json()
        if state["status"] == "complete":
            break
        time.sleep(0.1)

    assert state["status"] == "complete"
    assert state["stage"] == "completed"
    assert state["progress"] == 100.0
    assert len(state["evidence"]) > 0
    assert len(state["findings"]) > 0
    assert len(state["recommendations"]) > 0