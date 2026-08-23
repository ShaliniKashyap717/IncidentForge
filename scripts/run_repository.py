"""Run the Repository Agent on the payment_latency scenario."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.repository import RepositoryAgent
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


def main() -> None:
    """Load scenario data, run repository analysis, and print investigation outputs."""

    scenario = load_scenario("scenarios/payment_latency")
    incident_data = scenario.get("incident", {})
    if not isinstance(incident_data, dict):
        raise TypeError("Scenario incident data must be a dictionary.")

    incident = Incident.model_validate(incident_data)
    state_manager = InvestigationStateManager(incident)
    agent = RepositoryAgent()

    finding = agent.investigate(state_manager, scenario, use_llm=True)

    print("=== Repository Investigation ===")
    print(f"Incident: {incident.id} - {incident.title}")
    print(f"Summary: {finding.summary}")
    print(f"Hypothesis: {finding.hypothesis}")
    print(f"Confidence: {finding.confidence:.2f}")
    print()

    print("Evidence:")
    for item in finding.evidence:
        print(f"- [{item.type}] {item.source}: {item.description} (relevance={item.relevance:.2f})")

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
