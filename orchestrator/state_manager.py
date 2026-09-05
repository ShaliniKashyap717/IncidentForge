"""Investigation State Manager: Tracks the live state of an incident investigation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models.evidence import Evidence
from models.incident import Incident
from models.investigation import Investigation
from models.recommendation import Recommendation
from models.finding import Finding
from models.hypothesis import Hypothesis
from models.state import IncidentState

from orchestrator.evidence_store import EvidenceStore


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

        self.pending_tasks: list[str] = []
        self.completed_tasks: list[str] = []

        self.timeline = InvestigationTimeline()
        self.status = "created"
        self.stage = "initialized"
        self.progress = 0.0
        self.error: str | None = None

        self.investigation_started_at = datetime.now()
        self.timeline.add_event("investigation_created", f"Incident {incident.id} created: {incident.title}")

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

    def set_stage(self, stage: str, progress: float | None = None) -> None:
        """Update the investigation stage and optional progress.

        Args:
            stage: Current stage (e.g., 'queued', 'running', 'analyzing', 'recommending', 'completed')
            progress: Optional progress percentage (0-100)
        """
        self.stage = stage
        if progress is not None:
            self.progress = max(0.0, min(100.0, progress))
        self.timeline.add_event("stage_changed", f"Stage: {stage} ({self.progress:.0f}%)")

    def mark_failed(self, error: str) -> None:
        """Mark the investigation as failed.

        Args:
            error: Error message describing the failure.
        """
        self.status = "failed"
        self.error = error
        self.stage = "failed"
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
        return {
            "incident_id": self.incident.id,
            "incident_title": self.incident.title,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "error": self.error,
            "evidence_count": self.evidence_store.count(),
            "findings_count": len(self.findings),
            "hypotheses_count": len(self.hypotheses),
            "recommendations_count": len(self.recommendations),
            "active_agents": list(self.active_agents),
            "completed_agents": list(self.completed_agents),
            "pending_tasks": self.pending_tasks,
            "completed_tasks": self.completed_tasks,
        }

    def export_state(self) -> dict[str, Any]:
        """Export the complete investigation state.

        Returns:
            Dictionary representation of the full state.
        """
        return {
            "incident": self.incident.model_dump(mode="json"),
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "error": self.error,
            "investigation_started_at": self.investigation_started_at.isoformat(),
            "evidence": self.evidence_store.export_to_dict(),
            "findings": [f.model_dump(mode="json") for f in self.findings],
            "hypotheses": [h.model_dump(mode="json") for h in self.hypotheses],
            "recommendations": [r.model_dump(mode="json") for r in self.recommendations],
            "active_agents": list(self.active_agents),
            "completed_agents": list(self.completed_agents),
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
            started_at=self.investigation_started_at,
            findings=self.findings,
            hypotheses=self.hypotheses,
            investigation_steps=self.completed_tasks,
        )

        return IncidentState(
            incident=self.incident,
            investigation=investigation,
            recommendations=self.recommendations,
        )

    def mark_complete(self) -> None:
        """Mark the investigation as complete."""
        self.status = "complete"
        self.stage = "completed"
        self.progress = 100.0
        self.timeline.add_event("investigation_completed", "Investigation concluded")
