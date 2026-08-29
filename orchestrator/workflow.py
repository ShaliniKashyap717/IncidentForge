"""Incident investigation workflow."""

from __future__ import annotations

from typing import Any

from agents.incident_commander.agent import IncidentCommander, create_incident_commander
from models.incident import Incident
from orchestrator.state_manager import InvestigationStateManager


class IncidentWorkflow:
    """
    Executes an IncidentForge investigation from incident creation
    through specialist dispatch using the Incident Commander.
    """

    def __init__(
        self,
        commander: IncidentCommander | None = None,
    ) -> None:
        self.commander = commander or create_incident_commander()

    async def start(
        self,
        incident: Incident,
        context: dict[str, Any],
        use_llm: bool = False,
    ) -> InvestigationStateManager:
        """
        Start an incident investigation.

        Args:
            incident: The incident to investigate.
            context: Full scenario context including logs, metrics, traces.
            use_llm: Whether to use LLM for coordination (default: False for deterministic tests).

        Returns:
            The live InvestigationStateManager.
        """

        state_manager = InvestigationStateManager(incident)

        state_manager.timeline.add_event(
            "investigation_started",
            f"Investigation started for {incident.id}",
            "Incident Commander",
        )

        # Use the Incident Commander to coordinate the investigation
        self.commander.investigate(state_manager, context, use_llm=use_llm)

        return state_manager