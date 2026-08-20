from models.evidence import Evidence, EvidenceType
from models.finding import Finding
from models.incident import Incident, IncidentSeverity
from models.investigation import Investigation
from models.state import IncidentState


def test_incident_state():

    evidence = Evidence(
        type=EvidenceType.METRIC,
        source="prometheus",
        description="Checkout latency increased from 120ms to 4.5s.",
        relevance=0.95,
    )

    finding = Finding(
        agent="Observability Agent",
        summary="Checkout latency increased significantly.",
        hypothesis="Downstream service degradation",
        confidence=0.82,
        evidence=[evidence],
        next_actions=[
            "Investigate downstream inventory service latency."
        ],
    )

    incident = Incident(
        id="INC-001",
        title="Checkout API latency spike",
        description="Checkout requests are experiencing elevated latency.",
        severity=IncidentSeverity.HIGH,
        affected_services=["checkout-service"],
    )

    investigation = Investigation(
        started_at="2026-08-20T15:00:00",
        findings=[finding],
    )

    state = IncidentState(
        incident=incident,
        investigation=investigation,
    )

    assert state.incident.id == "INC-001"
    assert len(state.investigation.findings) == 1
    assert state.investigation.findings[0].confidence == 0.82