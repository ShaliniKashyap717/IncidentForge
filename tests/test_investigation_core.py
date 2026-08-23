"""Tests for the Investigation Core: Evidence Store, State Manager, and Recommendation Engine."""

import pytest

from models.evidence import Evidence, EvidenceType
from models.incident import Incident, IncidentSeverity
from models.finding import Finding
from models.hypothesis import Hypothesis
from models.recommendation import Recommendation

from orchestrator.evidence_store import EvidenceStore
from orchestrator.state_manager import InvestigationStateManager, InvestigationTimeline
from orchestrator.recommendation_engine import (
    combine_findings,
    rank_recommendations,
    merge_hypotheses,
    detect_conflicting_conclusions,
    generate_composite_recommendation,
)


# ==== EVIDENCE STORE TESTS ====


class TestEvidenceStore:
    def test_add_evidence_assigns_id(self):
        store = EvidenceStore()
        evidence = Evidence(
            type=EvidenceType.METRIC,
            source="prometheus",
            description="Latency spike detected",
            relevance=0.9,
        )

        evidence_id = store.add_evidence(evidence)
        assert evidence_id is not None
        retrieved = store.get_by_id(evidence_id)
        assert retrieved is not None
        assert retrieved.description == "Latency spike detected"

    def test_evidence_count(self):
        store = EvidenceStore()
        assert store.count() == 0

        store.add_evidence(Evidence(
            type=EvidenceType.LOG,
            source="app",
            description="Error occurred",
            relevance=0.8,
        ))

        assert store.count() == 1

    def test_get_by_source(self):
        store = EvidenceStore()
        store.add_evidence(Evidence(
            type=EvidenceType.METRIC,
            source="prometheus",
            description="CPU high",
            relevance=0.85,
        ))
        store.add_evidence(Evidence(
            type=EvidenceType.LOG,
            source="app",
            description="Error",
            relevance=0.9,
        ))

        prometheus_evidence = store.get_by_source("prometheus")
        assert len(prometheus_evidence) == 1
        assert prometheus_evidence[0].source == "prometheus"

    def test_get_by_type(self):
        store = EvidenceStore()
        store.add_evidence(Evidence(
            type=EvidenceType.METRIC,
            source="prometheus",
            description="Metric 1",
            relevance=0.9,
        ))
        store.add_evidence(Evidence(
            type=EvidenceType.LOG,
            source="app",
            description="Log 1",
            relevance=0.8,
        ))

        metrics = store.get_by_type(EvidenceType.METRIC)
        assert len(metrics) == 1
        assert metrics[0].type == EvidenceType.METRIC

    def test_get_sorted_by_confidence(self):
        store = EvidenceStore()
        store.add_evidence(Evidence(
            type=EvidenceType.METRIC,
            source="prom",
            description="Low confidence",
            relevance=0.3,
        ))
        store.add_evidence(Evidence(
            type=EvidenceType.METRIC,
            source="prom",
            description="High confidence",
            relevance=0.95,
        ))

        sorted_evidence = store.get_sorted_by_confidence(reverse=True)
        assert len(sorted_evidence) == 2
        assert sorted_evidence[0].relevance == 0.95
        assert sorted_evidence[1].relevance == 0.3

    def test_export_to_json(self):
        store = EvidenceStore()
        store.add_evidence(Evidence(
            type=EvidenceType.LOG,
            source="app",
            description="Test",
            relevance=0.9,
        ))

        json_str = store.export_to_json()
        assert "Test" in json_str
        assert "log" in json_str.lower()

    def test_merge_stores(self):
        store1 = EvidenceStore()
        store2 = EvidenceStore()

        store1.add_evidence(Evidence(
            type=EvidenceType.METRIC,
            source="prom1",
            description="Evidence 1",
            relevance=0.9,
        ))
        store2.add_evidence(Evidence(
            type=EvidenceType.LOG,
            source="app1",
            description="Evidence 2",
            relevance=0.8,
        ))

        store1.merge_from(store2)
        assert store1.count() == 2


# ==== INVESTIGATION TIMELINE TESTS ====


class TestInvestigationTimeline:
    def test_add_event(self):
        timeline = InvestigationTimeline()
        timeline.add_event("incident_created", "Incident created", None)

        events = timeline.get_events()
        assert len(events) == 1
        assert events[0]["type"] == "incident_created"
        assert events[0]["description"] == "Incident created"

    def test_events_ordered(self):
        timeline = InvestigationTimeline()
        timeline.add_event("event1", "First event")
        timeline.add_event("event2", "Second event")
        timeline.add_event("event3", "Third event")

        events = timeline.get_events()
        assert len(events) == 3
        assert events[0]["type"] == "event1"
        assert events[2]["type"] == "event3"

    def test_export_to_text(self):
        timeline = InvestigationTimeline()
        timeline.add_event("incident_created", "Incident started", None)
        timeline.add_event("agent_started", "Investigation began", "obs_agent")

        text = timeline.export_to_text()
        assert "Investigation Timeline" in text
        assert "incident_created" in text
        assert "obs_agent" in text


# ==== INVESTIGATION STATE MANAGER TESTS ====


class TestInvestigationStateManager:
    @pytest.fixture
    def incident(self):
        return Incident(
            id="INC-001",
            title="Test Incident",
            description="A test incident",
            severity=IncidentSeverity.HIGH,
            affected_services=["api"],
        )

    @pytest.fixture
    def state_manager(self, incident):
        return InvestigationStateManager(incident)

    def test_initialization(self, state_manager, incident):
        assert state_manager.incident == incident
        assert state_manager.status == "investigating"
        assert state_manager.evidence_store.count() == 0
        assert len(state_manager.findings) == 0

    def test_start_finish_agent(self, state_manager):
        state_manager.start_agent("ObservabilityAgent")
        assert "ObservabilityAgent" in state_manager.active_agents

        state_manager.finish_agent("ObservabilityAgent")
        assert "ObservabilityAgent" not in state_manager.active_agents
        assert "ObservabilityAgent" in state_manager.completed_agents

    def test_add_finding(self, state_manager):
        finding = Finding(
            agent="ObservabilityAgent",
            summary="Latency increased",
            hypothesis="Database bottleneck",
            confidence=0.85,
        )

        state_manager.add_finding(finding)
        assert len(state_manager.findings) == 1
        assert state_manager.findings[0].summary == "Latency increased"

    def test_add_evidence(self, state_manager):
        evidence = Evidence(
            type=EvidenceType.METRIC,
            source="prometheus",
            description="High latency detected",
            relevance=0.92,
        )

        evidence_id = state_manager.add_evidence(evidence)
        assert evidence_id is not None
        assert state_manager.evidence_store.count() == 1

    def test_add_recommendation(self, state_manager):
        rec = Recommendation(
            action="Scale up database",
            rationale="High load",
            risk="Low",
            confidence=0.8,
            requires_approval=True,
        )

        state_manager.add_recommendation(rec)
        assert len(state_manager.recommendations) == 1

    def test_add_complete_task(self, state_manager):
        state_manager.add_task("Investigate logs")
        assert "Investigate logs" in state_manager.pending_tasks

        state_manager.complete_task("Investigate logs")
        assert "Investigate logs" not in state_manager.pending_tasks
        assert "Investigate logs" in state_manager.completed_tasks

    def test_get_status_summary(self, state_manager):
        state_manager.start_agent("Agent1")
        state_manager.finish_agent("Agent1")

        summary = state_manager.get_status_summary()
        assert summary["incident_id"] == "INC-001"
        assert summary["status"] == "investigating"
        assert summary["evidence_count"] == 0
        assert "Agent1" in summary["completed_agents"]

    def test_export_state_json(self, state_manager):
        state_manager.start_agent("Agent1")
        state_manager.add_finding(Finding(
            agent="Agent1",
            summary="Test finding",
            hypothesis="Test hypothesis",
            confidence=0.9,
        ))

        json_str = state_manager.export_state_json()
        assert "Test finding" in json_str
        assert "INC-001" in json_str

    def test_mark_complete(self, state_manager):
        assert state_manager.status == "investigating"
        state_manager.mark_complete()
        assert state_manager.status == "complete"


# ==== RECOMMENDATION ENGINE TESTS ====


class TestRecommendationEngine:
    def test_combine_findings(self):
        findings = [
            Finding(
                agent="Agent1",
                summary="Database is slow",
                hypothesis="High load",
                confidence=0.85,
            ),
            Finding(
                agent="Agent2",
                summary="CPU utilization high",
                hypothesis="High load",
                confidence=0.80,
            ),
        ]

        combined = combine_findings(findings)
        assert combined["confidence"] == 0.825
        assert combined["agent_count"] == 2

    def test_combine_findings_empty(self):
        combined = combine_findings([])
        assert combined["confidence"] == 0.0
        assert combined["agent_count"] == 0

    def test_rank_recommendations(self):
        recs = [
            Recommendation(action="Action A", rationale="R1", risk="Low", confidence=0.6, requires_approval=False),
            Recommendation(action="Action B", rationale="R2", risk="Low", confidence=0.95, requires_approval=False),
            Recommendation(action="Action C", rationale="R3", risk="Low", confidence=0.7, requires_approval=False),
        ]

        ranked = rank_recommendations(recs)
        assert ranked[0].confidence == 0.95
        assert ranked[2].confidence == 0.6

    def test_merge_hypotheses_similar(self):
        hyps = [
            Hypothesis(description="Database bottleneck causing latency", confidence=0.8),
            Hypothesis(description="Database causing performance issues", confidence=0.75),
        ]

        merged = merge_hypotheses(hyps)
        assert len(merged) <= len(hyps)
        assert merged[0].confidence > 0.7

    def test_detect_conflicting_conclusions(self):
        findings = [
            Finding(agent="A1", summary="S1", hypothesis="Database slow", confidence=0.9),
            Finding(agent="A2", summary="S2", hypothesis="Network issue", confidence=0.8),
        ]

        conflicts = detect_conflicting_conclusions(findings)
        assert isinstance(conflicts, list)

    def test_generate_composite_recommendation(self):
        findings = [
            Finding(agent="A1", summary="Issue found", hypothesis="Root cause", confidence=0.85),
            Finding(agent="A2", summary="Confirmed", hypothesis="Root cause", confidence=0.90),
        ]
        hypotheses = [
            Hypothesis(description="Database degradation", confidence=0.87),
        ]

        rec = generate_composite_recommendation(findings, hypotheses)
        assert rec.confidence > 0.8
        assert rec.action is not None
