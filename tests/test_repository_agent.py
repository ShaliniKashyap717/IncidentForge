"""Tests for the Repository Agent and repository-tool integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.repository.agent import RepositoryAgent
from agents.repository.tools import (
    analyze_repository_change_correlation,
    analyze_repository_commits,
    analyze_repository_deployments,
    infer_incident_reference_timestamp,
)
from app.config import has_google_api_key
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "payment_latency"


def _state_manager_for(scenario: dict[str, object]) -> InvestigationStateManager:
    incident = Incident.model_validate(scenario["incident"])
    return InvestigationStateManager(incident)


def test_repository_agent_initialization() -> None:
    agent = RepositoryAgent()
    assert agent.name == "Repository Agent"
    assert agent.model_name == "gemini-3.6-flash"


def test_repository_tool_integration_outputs() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    incident = scenario["incident"]

    commits_result = analyze_repository_commits(
        scenario["commits"],
        affected_services=incident.get("affected_services", []),
    )
    deployments_result = analyze_repository_deployments(
        scenario["deployments"],
        affected_services=incident.get("affected_services", []),
        reference_timestamp=infer_incident_reference_timestamp(scenario),
    )
    correlation = analyze_repository_change_correlation(commits_result, deployments_result)

    assert commits_result["relevant_count"] >= 1
    assert len(deployments_result["sorted_deployments"]) >= 1
    assert "correlation_count" in correlation


def test_commit_and_deployment_evidence_creation() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=False)

    code_evidence = [e for e in finding.evidence if e.type.value == "code"]
    deployment_evidence = [e for e in finding.evidence if e.type.value == "deployment"]

    assert code_evidence
    assert deployment_evidence


def test_repository_finding_generation_and_confidence_bounds() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=False)

    assert finding.agent == "Repository Agent"
    assert finding.summary
    assert finding.hypothesis
    assert 0.0 <= finding.confidence <= 1.0


def test_evidence_to_finding_linkage_uses_state_evidence() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=False)
    stored = state_manager.evidence_store.get_all()

    for item in finding.evidence:
        assert any(
            s.type == item.type and s.source == item.source and s.description == item.description
            for s in stored
        )


def test_state_manager_timeline_task_and_agent_lifecycle() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()

    _ = agent.investigate(state_manager, scenario, use_llm=False)
    status = state_manager.get_status_summary()
    timeline = state_manager.timeline.get_events()

    assert "Repository Agent" in status["completed_agents"]
    assert "Analyze repository and deployment changes" in status["completed_tasks"]
    assert any(event["type"] == "repository_analyzed" for event in timeline)


def test_no_fabricated_commit_or_deployment_ids() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    known_shas = {entry["sha"] for entry in scenario["commits"]["commits"]}
    known_deployments = {entry["id"] for entry in scenario["deployments"]["deployments"]}

    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()
    finding = agent.investigate(state_manager, scenario, use_llm=False)

    evidence_text = "\n".join(item.description for item in finding.evidence)
    assert any(sha in evidence_text for sha in known_shas)
    assert any(deployment_id in evidence_text for deployment_id in known_deployments)


def test_repository_tool_failure_returns_graceful_finding() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    broken = dict(scenario)
    broken["deployments"] = {"deployments": "bad-type"}

    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()
    finding = agent.investigate(state_manager, broken, use_llm=False)

    assert finding.agent == "Repository Agent"
    assert finding.confidence <= 0.2
    assert any(event["type"] == "repository_error" for event in state_manager.timeline.get_events())


@pytest.mark.skipif(not has_google_api_key(), reason="GOOGLE_API_KEY not configured")
def test_repository_agent_live_llm_integration() -> None:
    scenario = load_scenario(SCENARIO_DIR)
    state_manager = _state_manager_for(scenario)
    agent = RepositoryAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=True)

    assert finding.agent == "Repository Agent"
    assert 0.0 <= finding.confidence <= 1.0
    assert finding.evidence
