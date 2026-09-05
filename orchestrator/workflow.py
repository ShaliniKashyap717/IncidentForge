"""Incident investigation workflow."""

from __future__ import annotations

import asyncio
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
        Start an incident investigation synchronously (for backward compatibility).

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

    async def start_background(
        self,
        incident: Incident,
        context: dict[str, Any],
        use_llm: bool = False,
    ) -> tuple[str, InvestigationStateManager]:
        """
        Start an incident investigation in the background.

        Args:
            incident: The incident to investigate.
            context: Full scenario context including logs, metrics, traces.
            use_llm: Whether to use LLM for coordination (default: False for deterministic tests).

        Returns:
            Tuple of (investigation_id, state_manager). The investigation runs in the background.
        """
        import uuid

        investigation_id = str(uuid.uuid4())
        state_manager = InvestigationStateManager(incident)
        state_manager.set_stage("queued", 0.0)

        # Store the state manager immediately so it can be polled
        # The actual investigation will be started as a background task
        asyncio.create_task(self._run_investigation(investigation_id, state_manager, context, use_llm))

        return investigation_id, state_manager

    async def _run_investigation(
        self,
        investigation_id: str,
        state_manager: InvestigationStateManager,
        context: dict[str, Any],
        use_llm: bool,
    ) -> None:
        """Run the investigation in the background."""
        try:
            state_manager.set_stage("running", 10.0)

            state_manager.timeline.add_event(
                "investigation_started",
                f"Investigation started for {state_manager.incident.id}",
                "Incident Commander",
            )

            # Use the Incident Commander to coordinate the investigation
            self.commander.investigate(state_manager, context, use_llm=use_llm)

            # mark_complete is called by the commander, but ensure stage is updated
            if state_manager.status == "complete":
                state_manager.set_stage("completed", 100.0)

        except Exception as exc:
            state_manager.mark_failed(str(exc))