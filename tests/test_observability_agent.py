"""Tests for the Observability Agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.observability.agent import ObservabilityAgent
from agents.observability.tools import analyze_logs, analyze_metrics, analyze_traces
from app.config import has_google_api_key
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "payment_latency"


def _make_state_manager(scenario: dict[str, object]) -> InvestigationStateManager:
    incident = Incident.model_validate(scenario["incident"])
    return InvestigationStateManager(incident)


def test_observability_agent_initialization() -> None:
    agent = ObservabilityAgent()
    assert agent.name == "Observability Agent"
    assert agent.model_name == "gemini-3.6-flash"


def test_telemetry_tool_integration_outputs() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    logs_result = analyze_logs(scenario["logs"], severity="ERROR")
    metrics_result = analyze_metrics(scenario["metrics"])
    traces_result = analyze_traces(scenario["traces"])

    assert logs_result["total_matches"] >= 1
    assert "statistics" in metrics_result
    assert "anomaly_window" in metrics_result
    assert len(traces_result["slow_spans"]) >= 1


def test_investigate_creates_finding_and_evidence_without_llm() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _make_state_manager(scenario)
    agent = ObservabilityAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=False)

    assert finding.agent == "Observability Agent"
    assert 0.0 <= finding.confidence <= 1.0
    assert finding.evidence
    assert len(finding.evidence) >= 3
    assert len(state_manager.findings) == 1
    assert state_manager.evidence_store.count() >= 3


def test_evidence_to_finding_linkage_uses_real_evidence() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _make_state_manager(scenario)
    agent = ObservabilityAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=False)
    stored = state_manager.evidence_store.get_all()

    for item in finding.evidence:
        assert any(
            s.type == item.type and s.source == item.source and s.description == item.description
            for s in stored
        )


def test_state_manager_integration_updates_agent_task_and_timeline() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _make_state_manager(scenario)
    agent = ObservabilityAgent()

    _ = agent.investigate(state_manager, scenario, use_llm=False)
    summary = state_manager.get_status_summary()
    timeline = state_manager.timeline.get_events()

    assert "Observability Agent" in summary["completed_agents"]
    assert "Analyze observability telemetry" in summary["completed_tasks"]
    assert any(event["type"] == "telemetry_analyzed" for event in timeline)


def test_tool_failure_handling_returns_graceful_finding() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _make_state_manager(scenario)
    agent = ObservabilityAgent()

    broken = dict(scenario)
    broken["metrics"] = {"series": "not-a-list"}

    finding = agent.investigate(state_manager, broken, use_llm=False)

    assert finding.agent == "Observability Agent"
    assert finding.confidence <= 0.2
    assert "failed" in finding.summary.lower() or "unavailable" in finding.hypothesis.lower()
    assert len(state_manager.findings) == 1
    assert any(event["type"] == "observability_error" for event in state_manager.timeline.get_events())


@pytest.mark.skipif(not has_google_api_key(), reason="GOOGLE_API_KEY not configured")
def test_observability_agent_live_llm_integration() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _make_state_manager(scenario)
    agent = ObservabilityAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=True)

    assert finding.agent == "Observability Agent"
    assert 0.0 <= finding.confidence <= 1.0
    assert finding.evidence
