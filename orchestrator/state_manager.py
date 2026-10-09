"""Investigation State Manager: Tracks the live state of an incident investigation."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from models.evidence import Evidence
from models.incident import Incident
from models.investigation import Investigation
from models.recommendation import Recommendation
from models.finding import Finding
from models.hypothesis import Hypothesis
from models.state import IncidentState

from orchestrator.evidence_store import EvidenceStore


class InvestigationStatus(str, Enum):
    """Canonical investigation status states."""
    QUEUED = "queued"
    RUNNING = "running"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationStage(str, Enum):
    """Canonical investigation stage states."""
    QUEUED = "queued"
    TRIAGE = "triage"
    OBSERVABILITY = "observability"
    REPOSITORY = "repository"
    DATABASE = "database"
    CORRELATION = "correlation"
    SYNTHESIS = "synthesis"
    RECOMMENDATION = "recommendation"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationTimeline:
    """Maintains an ordered timeline of investigation events."""

    def __init__(self) -> None:
        """Initialize an empty timeline."""
        self._events: list[dict[str, Any]] = []

    def add_event(self, event_type: str, description: str, agent: str | None = None) -> None:
        """Add an event to the timeline.

        Args:
            event_type: Type of event (e.g., 'incident_created', 'agent_started', 'evidence_added').
            description: Human-readable description of the event.
            agent: Optional agent name associated with the event.
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "description": description,
            "agent": agent,
        }
        self._events.append(event)

    def get_events(self) -> list[dict[str, Any]]:
        """Get all events in order."""
        return self._events

    def export_to_text(self) -> str:
        """Export timeline as formatted text."""
        lines = ["Investigation Timeline:"]
        lines.append("=" * 60)

        for event in self._events:
            timestamp = event["timestamp"].split("T")[1].split(".")[0]
            agent_info = f" [{event['agent']}]" if event["agent"] else ""
            lines.append(f"{timestamp} {event['type']}{agent_info}: {event['description']}")

        return "\n".join(lines)


class InvestigationStateManager:
    """Manages the live state of an incident investigation.

    Single source of truth for:
    - Incident details
    - Collected evidence
    - Agent findings
    - Active/completed agents
    - Tasks and timeline
    """

    def __init__(self, incident: Incident) -> None:
        """Initialize the state manager with an incident.

        Args:
            incident: The Incident object to investigate.
        """
        self.incident = incident
        self.evidence_store = EvidenceStore()
        self.findings: list[Finding] = []
        self.recommendations: list[Recommendation] = []
        self.hypotheses: list[Hypothesis] = []

        self.active_agents: set[str] = set()
        self.completed_agents: set[str] = set()
        self.selected_agents: set[str] = set()  # Agents selected during triage

        self.pending_tasks: list[str] = []
        self.completed_tasks: list[str] = []

        self.timeline = InvestigationTimeline()
        self.status = InvestigationStatus.QUEUED
        self.stage = InvestigationStage.QUEUED
        self.progress = 0.0
        self.error: str | None = None

        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.timeline.add_event("investigation_created", f"Incident {incident.id} created: {incident.title}")

    def set_selected_agents(self, agent_names: list[str]) -> None:
        """Record which agents were selected during triage.

        Args:
            agent_names: List of agent names selected for this investigation.
        """
        self.selected_agents.update(agent_names)
        for agent in agent_names:
            if agent not in self.active_agents and agent not in self.completed_agents:
                # Don't add to pending; just track as selected
                pass

    def start_agent(self, agent_name: str) -> None:
        """Mark an agent as started.

        Args:
            agent_name: Name of the agent starting investigation.
        """
        self.active_agents.add(agent_name)
        self.timeline.add_event("agent_started", f"Agent began investigation", agent_name)

    def finish_agent(self, agent_name: str) -> None:
        """Mark an agent as finished.

        Args:
            agent_name: Name of the agent completing investigation.
        """
        if agent_name in self.active_agents:
            self.active_agents.remove(agent_name)
        self.completed_agents.add(agent_name)
        self.timeline.add_event("agent_finished", f"Agent completed investigation", agent_name)

    def add_finding(self, finding: Finding) -> None:
        """Add a finding from an agent.

        Args:
            finding: A Finding object to add to the investigation.
        """
        self.findings.append(finding)
        self.timeline.add_event(
            "finding_added",
            f"Finding: {finding.summary}",
            finding.agent,
        )

    def add_evidence(self, evidence_obj: Evidence) -> str:
        """Add evidence to the store.

        Args:
            evidence_obj: An Evidence object.

        Returns:
            The ID of the added evidence.
        """
        evidence_id = self.evidence_store.add_evidence(evidence_obj, deduplicate=True)
        evidence = self.evidence_store.get_by_id(evidence_id)
        if evidence:
            self.timeline.add_event(
                "evidence_added",
                f"Evidence ({evidence.type}): {evidence.description}",
                evidence.source,
            )
        return evidence_id

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation to the investigation.

        Args:
            recommendation: A Recommendation object.
        """
        self.recommendations.append(recommendation)
        self.timeline.add_event(
            "recommendation_added",
            f"Recommendation: {recommendation.action}",
        )

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Add a hypothesis to the investigation.

        Args:
            hypothesis: A Hypothesis object.
        """
        self.hypotheses.append(hypothesis)
        self.timeline.add_event(
            "hypothesis_proposed",
            f"Hypothesis: {hypothesis.description} (confidence={hypothesis.confidence:.2f})",
        )

    def set_stage(self, stage: str | InvestigationStage, progress: float | None = None) -> None:
        """Update the investigation stage and optional progress.

        Args:
            stage: Current stage (e.g., 'queued', 'running', 'analyzing', 'recommending', 'completed')
            progress: Optional progress percentage (0-100)
        """
        stage_value = stage.value if isinstance(stage, InvestigationStage) else stage
        self.stage = stage_value
        if progress is not None:
            self.progress = max(0.0, min(100.0, progress))

        # Update status based on stage
        if stage_value in (InvestigationStage.QUEUED.value, "queued"):
            self.status = InvestigationStatus.QUEUED
        elif stage_value in (InvestigationStage.TRIAGE.value, InvestigationStage.OBSERVABILITY.value,
                             InvestigationStage.REPOSITORY.value, InvestigationStage.DATABASE.value,
                             InvestigationStage.CORRELATION.value, "triaging", "observability", "repository", "database", "correlation"):
            self.status = InvestigationStatus.RUNNING if self.status == InvestigationStatus.QUEUED else self.status
            if "analyz" in stage_value.lower() or stage_value in (InvestigationStage.OBSERVABILITY.value, InvestigationStage.REPOSITORY.value, InvestigationStage.DATABASE.value, InvestigationStage.CORRELATION.value):
                self.status = InvestigationStatus.ANALYZING
        elif stage_value in (InvestigationStage.SYNTHESIS.value, InvestigationStage.RECOMMENDATION.value, "synthesis", "recommending"):
            self.status = InvestigationStatus.SYNTHESIZING
        elif stage_value in (InvestigationStage.COMPLETED.value, "completed"):
            self.status = InvestigationStatus.COMPLETED
        elif stage_value in (InvestigationStage.FAILED.value, "failed"):
            self.status = InvestigationStatus.FAILED

        self.timeline.add_event("stage_changed", f"Stage: {stage_value} ({self.progress:.0f}%)")

    def mark_failed(self, error: str) -> None:
        """Mark the investigation as failed.

        Args:
            error: Error message describing the failure.
        """
        self.status = InvestigationStatus.FAILED
        self.error = error
        self.stage = InvestigationStage.FAILED
        self.completed_at = datetime.now()
        self.timeline.add_event("investigation_failed", f"Investigation failed: {error}")

    def add_task(self, task_description: str) -> None:
        """Add a pending task.

        Args:
            task_description: Description of the task.
        """
        self.pending_tasks.append(task_description)
        self.timeline.add_event("task_added", f"Task: {task_description}")

    def complete_task(self, task_description: str) -> None:
        """Mark a task as completed.

        Args:
            task_description: Description of the task to complete.
        """
        if task_description in self.pending_tasks:
            self.pending_tasks.remove(task_description)
        self.completed_tasks.append(task_description)
        self.timeline.add_event("task_completed", f"Task completed: {task_description}")

    def get_status_summary(self) -> dict[str, Any]:
        """Get a summary of the current investigation status.

        Returns:
            Dictionary with status information.
        """
        status_value = self.status.value if isinstance(self.status, InvestigationStatus) else self.status
        stage_value = self.stage.value if isinstance(self.stage, InvestigationStage) else self.stage
        return {
            "incident_id": self.incident.id,
            "incident_title": self.incident.title,
            "status": status_value,
            "stage": stage_value,
            "progress": self.progress,
            "error": self.error,
            "evidence_count": self.evidence_store.count(),
            "findings_count": len(self.findings),
            "hypotheses_count": len(self.hypotheses),
            "recommendations_count": len(self.recommendations),
            "active_agents": list(self.active_agents),
            "completed_agents": list(self.completed_agents),
            "selected_agents": list(self.selected_agents),
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def export_state(self) -> dict[str, Any]:
        """Export the complete investigation state.

        Returns:
            Dictionary representation of the full state.
        """
        return {
            "incident": self.incident.model_dump(mode="json"),
            "status": self.status.value if isinstance(self.status, InvestigationStatus) else self.status,
            "stage": self.stage.value if isinstance(self.stage, InvestigationStage) else self.stage,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "evidence": self.evidence_store.export_to_dict(),
            "findings": [f.model_dump(mode="json") for f in self.findings],
            "hypotheses": [h.model_dump(mode="json") for h in self.hypotheses],
            "recommendations": [r.model_dump(mode="json") for r in self.recommendations],
            "active_agents": list(self.active_agents),
            "completed_agents": list(self.completed_agents),
            "selected_agents": list(self.selected_agents),
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
            "timeline": self.timeline.get_events(),
        }

    def export_state_json(self) -> str:
        """Export the investigation state as JSON.

        Returns:
            JSON string representation of the state.
        """
        return json.dumps(self.export_state(), indent=2, default=str)

    def to_incident_state(self) -> IncidentState:
        """Convert to an IncidentState model.

        Returns:
            IncidentState object suitable for passing to agents.
        """
        investigation = Investigation(
            started_at=self.started_at or self.created_at,
            findings=self.findings,
            hypotheses=self.hypotheses,
            investigation_steps=self.completed_tasks,
        )

        return IncidentState(
            incident=self.incident,
            investigation=investigation,
            recommendations=self.recommendations,
        )

    def start_investigation(self) -> None:
        """Mark the investigation as started (moves from queued to running)."""
        if self.status == InvestigationStatus.QUEUED:
            self.status = InvestigationStatus.RUNNING
            self.stage = InvestigationStage.TRIAGE
            self.progress = 5.0
            self.started_at = datetime.now()
            self.timeline.add_event("investigation_started", f"Investigation started for {self.incident.id}", "Incident Commander")

    def mark_complete(self) -> None:
        """Mark the investigation as complete."""
        self.status = InvestigationStatus.COMPLETED
        self.stage = InvestigationStage.COMPLETED
        self.progress = 100.0
        self.completed_at = datetime.now()
        self.timeline.add_event("investigation_completed", "Investigation concluded")
