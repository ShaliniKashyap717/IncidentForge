"""Tests for the Database Agent and database tool integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.database.agent import DatabaseAgent
from agents.database.tools import (
    analyze_database_locks,
    analyze_database_metrics,
    analyze_database_queries,
    build_database_tools,
)
from app.config import has_google_api_key
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "payment_latency"


def _state_manager_for(scenario: dict[str, object]) -> InvestigationStateManager:
    incident = Incident.model_validate(scenario["incident"])
    return InvestigationStateManager(incident)


def test_database_agent_initialization() -> None:
    agent = DatabaseAgent()
    assert agent.name == "Database Agent"
    assert agent.model_name == "gemini-3.6-flash"


def test_adk_agent_configuration_and_tools() -> None:
    agent = DatabaseAgent()
    assert agent.adk_agent.name == "database_agent"
    assert agent.adk_agent.output_schema is not None
    tool_names = [tool.name for tool in build_database_tools()]
    assert "analyze_database_queries" in tool_names
    assert "analyze_database_locks" in tool_names
    assert "analyze_database_metrics" in tool_names


def test_database_tool_integration_outputs() -> None:
    scenario = load_scenario(SCENARIO_DIR)

    query_result = analyze_database_queries(scenario["traces"])
    lock_result = analyze_database_locks(scenario["logs"], query_result["database_spans"])
    metrics_result = analyze_database_metrics(query_result["database_spans"], scenario["incident"]["title"])

    assert query_result["summary"]["count"] >= 1
    assert isinstance(lock_result["lock_summary"], str)
    assert "is_anomalous" in metrics_result["anomaly"]


def test_database_evidence_generation_and_finding() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()

    finding = agent.investigate(manager, scenario, use_llm=False)

    assert finding.agent == "Database Agent"
    assert finding.evidence
    assert any(item.type.value == "database" for item in finding.evidence)
    assert 0.0 <= finding.confidence <= 1.0


def test_evidence_to_finding_linkage() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()

    finding = agent.investigate(manager, scenario, use_llm=False)
    stored = manager.evidence_store.get_all()

    for item in finding.evidence:
        assert any(
            s.type == item.type and s.source == item.source and s.description == item.description
            for s in stored
        )


def test_state_manager_integration_and_timeline() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()

    _ = agent.investigate(manager, scenario, use_llm=False)
    summary = manager.get_status_summary()
    events = manager.timeline.get_events()

    assert "Database Agent" in summary["completed_agents"]
    assert "Analyze database behavior" in summary["completed_tasks"]
    assert any(event["type"] == "database_analyzed" for event in events)


def test_graceful_database_tool_failure() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    broken = dict(scenario)
    broken["traces"] = {"traces": "bad"}

    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()
    finding = agent.investigate(manager, broken, use_llm=False)

    assert finding.agent == "Database Agent"
    assert finding.confidence <= 0.2
    assert any(event["type"] == "database_error" for event in manager.timeline.get_events())


def test_no_fabricated_database_evidence() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()

    finding = agent.investigate(manager, scenario, use_llm=False)
    text = "\n".join(item.description for item in finding.evidence)

    assert "payments_db.query" in text or "database spans" in text


@pytest.mark.skipif(not has_google_api_key(), reason="GOOGLE_API_KEY not configured")
def test_database_agent_live_llm_integration() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    manager = _state_manager_for(scenario)
    agent = DatabaseAgent()

    finding = agent.investigate(manager, scenario, use_llm=True)

    assert finding.agent == "Database Agent"
    assert 0.0 <= finding.confidence <= 1.0
    assert finding.evidence
