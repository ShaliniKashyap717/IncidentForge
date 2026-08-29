"""Tests for the end-to-end investigation runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from orchestrator.workflow import IncidentWorkflow
from scripts.load_scenarios import load_scenario

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "payment_latency"


@pytest.fixture
def scenario() -> dict[str, object]:
    """Load the payment_latency scenario."""
    return load_scenario(SCENARIO_DIR)


@pytest.fixture
def incident(scenario: dict[str, object]) -> Incident:
    """Create an Incident model from the scenario."""
    incident_data = scenario.get("incident", {})
    return Incident.model_validate(incident_data)


@pytest.fixture
def state_manager(incident: Incident) -> InvestigationStateManager:
    """Create an InvestigationStateManager."""
    return InvestigationStateManager(incident)


def test_scenario_loads_successfully(scenario: dict[str, object]) -> None:
    """Test that the payment_latency scenario can be loaded."""
    assert scenario["name"] == "payment_latency"
    assert "incident" in scenario
    assert "logs" in scenario
    assert "metrics" in scenario
    assert "traces" in scenario
    assert "deployments" in scenario
    assert "commits" in scenario

    # Verify incident structure
    incident_data = scenario["incident"]
    assert incident_data["id"] == "INC-2026-1042"
    assert incident_data["title"] == "Payment API latency spike"
    assert incident_data["severity"] == "high"
    assert set(incident_data["affected_services"]) == {
        "checkout-api",
        "payment-api",
        "inventory-api",
    }

    # Verify telemetry data exists
    assert len(scenario["logs"]) > 0
    assert "series" in scenario["metrics"]
    assert len(scenario["metrics"]["series"]) > 0
    assert "traces" in scenario["traces"]
    assert len(scenario["traces"]["traces"]) > 0
    # Each trace has slow_spans
    assert "slow_spans" in scenario["traces"]["traces"][0]


def test_workflow_creates_state_manager(incident: Incident, scenario: dict[str, object]) -> None:
    """Test that the workflow creates a state manager with the correct incident."""
    workflow = IncidentWorkflow()

    import asyncio

    state_manager = asyncio.run(workflow.start(incident, scenario, use_llm=False))

    assert isinstance(state_manager, InvestigationStateManager)
    assert state_manager.incident.id == incident.id
    assert state_manager.incident.title == incident.title


def test_observability_agent_is_selected(state_manager: InvestigationStateManager) -> None:
    """Test that the observability agent is selected and executed."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    # Run the investigation
    commander.investigate(state_manager, scenario, use_llm=False)

    # Check that observability agent was invoked
    summary = state_manager.get_status_summary()
    assert "Observability Agent" in summary["completed_agents"]
    assert "Incident Commander" in summary["completed_agents"]


def test_logs_metrics_traces_are_analyzed(state_manager: InvestigationStateManager) -> None:
    """Test that logs, metrics, and traces are analyzed and produce evidence."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    commander.investigate(state_manager, scenario, use_llm=False)

    # Check evidence was collected for all three types
    evidence = state_manager.evidence_store.get_all()
    evidence_types = {e.type.value for e in evidence}

    assert "metric" in evidence_types
    assert "log" in evidence_types
    assert "trace" in evidence_types
    assert len(evidence) >= 3


def test_evidence_is_added_to_state_manager(state_manager: InvestigationStateManager) -> None:
    """Test that evidence is properly added through InvestigationStateManager.add_evidence()."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    initial_count = state_manager.evidence_store.count()
    assert initial_count == 0

    commander.investigate(state_manager, scenario, use_llm=False)

    final_count = state_manager.evidence_store.count()
    assert final_count >= 3
    assert final_count > initial_count


def test_finding_is_produced(state_manager: InvestigationStateManager) -> None:
    """Test that at least one Finding is produced and added to the state manager."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    assert len(state_manager.findings) == 0

    commander.investigate(state_manager, scenario, use_llm=False)

    assert len(state_manager.findings) >= 1
    finding = state_manager.findings[0]
    assert finding.agent == "Observability Agent"
    assert finding.summary
    assert finding.hypothesis
    assert 0.0 <= finding.confidence <= 1.0
    assert len(finding.evidence) >= 3


def test_final_state_contains_expected_incident_id(state_manager: InvestigationStateManager) -> None:
    """Test that the final state contains the expected incident ID."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    commander.investigate(state_manager, scenario, use_llm=False)

    exported = state_manager.export_state()
    assert exported["incident"]["id"] == "INC-2026-1042"
    assert exported["incident"]["title"] == "Payment API latency spike"


def test_final_state_contains_nonzero_evidence_count(state_manager: InvestigationStateManager) -> None:
    """Test that the final state contains a non-zero evidence count."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    commander.investigate(state_manager, scenario, use_llm=False)

    exported = state_manager.export_state()
    # export_state returns evidence as a list from evidence_store.export_to_dict()
    assert isinstance(exported["evidence"], list)
    assert len(exported["evidence"]) >= 3


def test_final_state_contains_at_least_one_finding(state_manager: InvestigationStateManager) -> None:
    """Test that the final state contains at least one finding."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    commander.investigate(state_manager, scenario, use_llm=False)

    exported = state_manager.export_state()
    assert len(exported["findings"]) >= 1
    assert exported["findings"][0]["agent"] == "Observability Agent"


def test_timeline_contains_key_events(state_manager: InvestigationStateManager) -> None:
    """Test that the timeline contains key investigation events."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    commander.investigate(state_manager, scenario, use_llm=False)

    timeline = state_manager.timeline.get_events()
    event_types = {event["type"] for event in timeline}

    # Events added by IncidentCommander.investigate()
    assert "incident_created" in event_types
    assert "commander_triage" in event_types
    assert "agent_started" in event_types
    assert "evidence_added" in event_types
    assert "finding_added" in event_types
    assert "telemetry_analyzed" in event_types
    assert "agent_finished" in event_types
    assert "agent_completed" in event_types
    assert "investigation_coordinated" in event_types


def test_investigation_completes_without_errors(state_manager: InvestigationStateManager) -> None:
    """Test that the investigation completes without errors."""
    from agents.incident_commander.agent import create_incident_commander

    commander = create_incident_commander()
    scenario = load_scenario(SCENARIO_DIR)

    # Should not raise any exceptions
    commander.investigate(state_manager, scenario, use_llm=False)

    # Status should be investigating (not complete, since we didn't mark it complete)
    assert state_manager.status == "investigating"

    # No error events in timeline
    timeline = state_manager.timeline.get_events()
    error_events = [e for e in timeline if "error" in e["type"].lower()]
    assert len(error_events) == 0