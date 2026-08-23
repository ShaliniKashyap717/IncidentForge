"""Run the Observability Agent on the payment_latency scenario."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.observability import ObservabilityAgent
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


def main() -> None:
    """Load the scenario, run the Observability Agent, and print the final state."""

    scenario = load_scenario("scenarios/payment_latency")
    incident_data = scenario.get("incident", {})
    if not isinstance(incident_data, dict):
        raise TypeError("Scenario incident data must be a dictionary.")

    incident = Incident.model_validate(incident_data)
    state_manager = InvestigationStateManager(incident)
    agent = ObservabilityAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=True)

    print("=== Observability Investigation ===")
    print(f"Incident: {incident.id} - {incident.title}")
    print(f"Summary: {finding.summary}")
    print(f"Hypothesis: {finding.hypothesis}")
    print(f"Confidence: {finding.confidence:.2f}")
    print()
    print("Evidence:")
    for evidence in finding.evidence:
        print(f"- [{evidence.type}] {evidence.source}: {evidence.description} (relevance={evidence.relevance:.2f})")
    print()
    print("Next actions:")
    for action in finding.next_actions:
        print(f"- {action}")
    print()
    print("Timeline:")
    print(state_manager.timeline.export_to_text())
    print()
    print("Exported state:")
    print(state_manager.export_state_json())


if __name__ == "__main__":
    main()