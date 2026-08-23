"""Demo script for the Investigation Core using the payment_latency scenario."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.evidence import Evidence, EvidenceType
from models.finding import Finding
from models.hypothesis import Hypothesis
from models.recommendation import Recommendation
from orchestrator.evidence_store import EvidenceStore
from orchestrator.recommendation_engine import (
    combine_findings,
    generate_composite_recommendation,
    merge_hypotheses,
    rank_recommendations,
)
from orchestrator.state_manager import InvestigationStateManager
from scripts.load_scenarios import load_scenario


def build_sample_findings() -> list[Finding]:
    """Create a small deterministic set of sample findings for the demo."""
    return [
        Finding(
            agent="Observability Agent",
            summary="Payment latency spiked in the payment-api service.",
            hypothesis="Downstream dependency and retry behavior caused elevated latency.",
            confidence=0.91,
        ),
        Finding(
            agent="Observability Agent",
            summary="Slow traces cluster around payment authorization and inventory reservation.",
            hypothesis="Downstream dependency and retry behavior caused elevated latency.",
            confidence=0.88,
        ),
    ]


def build_sample_evidence() -> list[Evidence]:
    """Create deterministic sample evidence for the investigation demo."""
    return [
        Evidence(
            type=EvidenceType.METRIC,
            source="payment-api",
            description="p99 latency rose from ~250ms to ~6.1s.",
            relevance=0.95,
        ),
        Evidence(
            type=EvidenceType.TRACE,
            source="payment-api",
            description="Slow spans concentrated in payment.authorize and inventory.reserve.",
            relevance=0.93,
        ),
        Evidence(
            type=EvidenceType.LOG,
            source="payment-api",
            description="Timeout and retry warnings appeared during the spike window.",
            relevance=0.86,
        ),
    ]


def build_sample_recommendations() -> list[Recommendation]:
    """Create deterministic next-step recommendations."""
    return [
        Recommendation(
            action="Inspect the payment-api deployment and retry configuration.",
            rationale="The latency spike aligns with a recent deployment window and retry changes.",
            risk="Low",
            confidence=0.92,
            requires_approval=False,
        ),
        Recommendation(
            action="Review downstream inventory-api and database latency during the same window.",
            rationale="Trace data shows downstream time contributing materially to end-to-end latency.",
            risk="Low",
            confidence=0.88,
            requires_approval=False,
        ),
    ]


def main() -> None:
    """Run the investigation core demo and print a readable summary."""
    scenario = load_scenario("scenarios/payment_latency")
    state = InvestigationStateManager(
        incident=state_incident_from_scenario(scenario),
    )

    evidence_store = EvidenceStore()
    for evidence in build_sample_evidence():
        evidence_store.add_evidence(evidence)
        state.add_evidence(evidence)

    findings = build_sample_findings()
    for finding in findings:
        state.add_finding(finding)

    recommendations = build_sample_recommendations()
    for recommendation in recommendations:
        state.add_recommendation(recommendation)

    combined = combine_findings(findings)
    hypotheses = merge_hypotheses(
        [
            Hypothesis(
                description=finding.hypothesis,
                confidence=finding.confidence,
            )
            for finding in findings
        ]
    )
    ranked_recommendations = rank_recommendations(recommendations)
    composite_recommendation = generate_composite_recommendation(findings, hypotheses)

    print("=== IncidentForge Investigation Demo ===")
    print(f"Incident: {state.incident.id} - {state.incident.title}")
    print(f"Status: {state.status}")
    print(f"Evidence Count: {state.evidence_store.count()}")
    print(f"Finding Count: {len(state.findings)}")
    print()

    print("-- Combined Finding Summary --")
    print(combined["summary"])
    print(f"Confidence: {combined['confidence']:.2f}")
    print()

    print("-- Ranked Recommendations --")
    for index, recommendation in enumerate(ranked_recommendations, start=1):
        print(f"{index}. {recommendation.action} (confidence={recommendation.confidence:.2f})")
    print()

    print("-- Composite Recommendation --")
    print(composite_recommendation.action)
    print(composite_recommendation.rationale)
    print()

    print("-- Timeline --")
    print(state.timeline.export_to_text())

    print()
    print("-- Exported State --")
    print(state.export_state_json())


def state_incident_from_scenario(scenario: dict[str, object]):
    """Build an Incident model from loaded scenario data."""
    from models.incident import Incident

    incident_data = scenario["incident"]
    if not isinstance(incident_data, dict):
        raise TypeError("Scenario incident data must be a dictionary.")
    return Incident.model_validate(incident_data)


if __name__ == "__main__":
    main()
