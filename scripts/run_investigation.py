"""Run a full end-to-end investigation on a scenario."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from orchestrator.workflow import IncidentWorkflow
from scripts.load_scenarios import load_scenario


def print_investigation_report(state_manager: InvestigationStateManager) -> None:
    """Print a concise final investigation report."""

    incident = state_manager.incident
    summary = state_manager.get_status_summary()

    print("=== INCIDENT ===")
    print(f"ID: {incident.id}")
    print(f"Title: {incident.title}")
    print(f"Severity: {incident.severity.value}")
    print(f"Affected services: {', '.join(incident.affected_services) or 'none'}")
    print()

    print("=== INVESTIGATION STATUS ===")
    print(f"Status: {summary['status']}")
    print(f"Agents completed: {', '.join(summary['completed_agents']) or 'none'}")
    print(f"Evidence collected: {summary['evidence_count']}")
    print(f"Findings: {summary['findings_count']}")
    print()

    # Print observability finding if available
    observability_findings = [
        f for f in state_manager.findings if f.agent == "Observability Agent"
    ]
    if observability_findings:
        finding = observability_findings[0]
        print("=== OBSERVABILITY FINDING ===")
        print(f"Summary: {finding.summary}")
        print(f"Hypothesis: {finding.hypothesis}")
        print(f"Confidence: {finding.confidence:.2f}")
        print()

    # Print all evidence
    evidence = state_manager.evidence_store.get_all()
    if evidence:
        print("=== EVIDENCE ===")
        for e in evidence:
            print(f"- [{e.type.value}] {e.source}: {e.description} (relevance={e.relevance:.2f})")
        print()

    # Print recommendations
    if state_manager.recommendations:
        print("=== RECOMMENDATIONS ===")
        for rec in state_manager.recommendations:
            print(f"- [{rec.priority.value}] {rec.action} ({rec.rationale})")
        print()

    # Print timeline
    print("=== TIMELINE ===")
    timeline_text = state_manager.timeline.export_to_text()
    for line in timeline_text.split("\n"):
        print(line)


async def run_investigation(scenario_dir: str, use_llm: bool = False) -> InvestigationStateManager:
    """Run a full investigation on the given scenario directory."""

    # Load scenario
    scenario = load_scenario(scenario_dir)

    # Create Incident model from scenario
    incident_data = scenario.get("incident", {})
    if not isinstance(incident_data, dict):
        raise TypeError("Scenario incident data must be a dictionary.")

    incident = Incident.model_validate(incident_data)

    # Create workflow and execute investigation
    workflow = IncidentWorkflow()
    state_manager = await workflow.start(incident, scenario, use_llm=use_llm)

    return state_manager


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an end-to-end IncidentForge investigation on a scenario."
    )
    parser.add_argument(
        "scenario_dir",
        help="Path to the scenario directory (e.g., scenarios/payment_latency)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for coordination and finding generation (requires GOOGLE_API_KEY)",
    )
    args = parser.parse_args()

    try:
        state_manager = asyncio.run(run_investigation(args.scenario_dir, use_llm=args.use_llm))
        print_investigation_report(state_manager)

    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()