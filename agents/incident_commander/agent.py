"""Incident Commander agent implementation using Google ADK."""

from __future__ import annotations

import json
from typing import Any

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.incident_commander.prompt import (
    build_finding_synthesis_prompt,
    build_incident_commander_instruction,
    build_investigation_context_prompt,
)
from agents.observability.agent import ObservabilityAgent
from app.config import get_gemini_model_name, has_google_api_key
from models.finding import Finding
from models.state import IncidentState
from orchestrator.state_manager import InvestigationStateManager


class IncidentCommander:
    """Top-level investigation coordinator that manages specialist agents."""

    def __init__(
        self,
        model_name: str | None = None,
        app_name: str = "incidentforge",
    ) -> None:
        """Initialize the Incident Commander.

        Args:
            model_name: Optional model override.
            app_name: Application name for ADK sessions.
        """

        self.name = "Incident Commander"
        self.model_name = model_name or get_gemini_model_name()
        self.app_name = app_name
        self.session_service = InMemorySessionService()
        self.observability_agent = ObservabilityAgent(model_name=model_name, app_name=app_name)

        self.adk_agent = Agent(
            name="incident_commander",
            model=self.model_name,
            instruction=build_incident_commander_instruction(),
            tools=[],
            mode="single_turn",
        )

    def investigate(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool = True,
    ) -> list[Finding]:
        """Run the full investigation coordination.

        This method:
        1. Performs initial triage to select specialist agents
        2. Invokes each selected agent with appropriate context
        3. Collects findings from all agents
        4. Optionally synthesizes findings into hypotheses and recommendations

        Args:
            state_manager: Shared investigation state manager.
            scenario: Full scenario data including incident and telemetry.
            use_llm: Whether to use LLM for coordination decisions.

        Returns:
            List of all findings produced by specialist agents.
        """

        state_manager.start_agent(self.name)
        state_manager.add_task("Coordinate incident investigation")

        all_findings: list[Finding] = []

        try:
            selected_agents = self._triage(state_manager, scenario, use_llm)

            for agent_name in selected_agents:
                if agent_name == "observability":
                    finding = self._invoke_observability_agent(
                        state_manager,
                        scenario,
                        use_llm,
                    )
                    all_findings.append(finding)
                else:
                    state_manager.timeline.add_event(
                        "agent_skipped",
                        f"Agent {agent_name} not yet implemented",
                        self.name,
                    )

            if use_llm and has_google_api_key() and all_findings:
                self._synthesize_findings(state_manager, scenario, all_findings, use_llm)

            state_manager.complete_task("Coordinate incident investigation")
            state_manager.timeline.add_event(
                "investigation_coordinated",
                f"Coordinated {len(all_findings)} specialist agent(s)",
                self.name,
            )
            state_manager.finish_agent(self.name)

            return all_findings

        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            state_manager.timeline.add_event(
                "commander_error",
                f"Incident Commander coordination failed: {exc}",
                self.name,
            )
            state_manager.complete_task("Coordinate incident investigation")
            state_manager.finish_agent(self.name)
            return all_findings

    def _triage(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> list[str]:
        """Determine which specialist agents should participate.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether to use LLM for triage decision.

        Returns:
            List of selected agent names.
        """

        if use_llm and has_google_api_key():
            try:
                state_summary = self._build_state_summary(state_manager, scenario)
                return self._llm_triage(state_summary)
            except (RuntimeError, ValueError, KeyError, TypeError):
                # LLM triage failed; fall back to deterministic triage
                pass

        return self._deterministic_triage(state_manager, scenario)

    def _deterministic_triage(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
    ) -> list[str]:
        """Deterministic fallback triage: always start with observability.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.

        Returns:
            List of agent names to invoke.
        """

        selected = ["observability"]
        incident = state_manager.incident

        state_manager.add_task(f"Investigate incident: {incident.title}")
        state_manager.timeline.add_event(
            "commander_triage",
            f"Commander selected agents: {', '.join(selected)}",
            self.name,
        )

        return selected

    def _llm_triage(self, state_summary: str) -> list[str]:
        """Use LLM to decide which agents to invoke.

        Args:
            state_summary: Text summary of investigation state.

        Returns:
            List of selected agent names.
        """

        session = self.session_service.create_session_sync(
            app_name=self.app_name,
            user_id="incidentforge",
            state={},
        )
        runner = Runner(
            agent=self.adk_agent,
            session_service=self.session_service,
            app_name=self.app_name,
        )

        prompt = build_investigation_context_prompt(state_summary)
        user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

        final_output: str | None = None
        for event in runner.run(
            user_id="incidentforge",
            session_id=session.id,
            new_message=user_message,
        ):
            if event.output is not None:
                final_output = str(event.output)

        if not final_output:
            return ["observability"]

        try:
            decision = json.loads(final_output)
            agents = decision.get("selected_agents", ["observability"])
            return [a for a in agents if a in self._available_agents()]
        except (json.JSONDecodeError, AttributeError):
            return ["observability"]

    def _available_agents(self) -> list[str]:
        """Return list of currently implemented specialist agents."""
        return ["observability"]

    def _build_state_summary(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
    ) -> str:
        """Build a text summary of the current investigation state.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.

        Returns:
            Formatted state summary.
        """

        incident = state_manager.incident
        evidence = state_manager.evidence_store.get_all()

        lines = [
            f"Incident: {incident.id} - {incident.title}",
            f"Severity: {incident.severity.value}",
            f"Description: {incident.description}",
            f"Affected Services: {', '.join(incident.affected_services) or 'none'}",
            f"Status: {incident.status.value}",
            "",
            f"Evidence Count: {len(evidence)}",
        ]

        if evidence:
            lines.append("Evidence:")
            for e in evidence:
                lines.append(f"  - [{e.type.value}] {e.source}: {e.description[:100]} (relevance={e.relevance:.2f})")

        if state_manager.findings:
            lines.append("\nExisting Findings:")
            for f in state_manager.findings:
                lines.append(f"  - {f.agent}: {f.summary[:100]} (confidence={f.confidence:.2f})")

        return "\n".join(lines)

    def _invoke_observability_agent(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        use_llm: bool,
    ) -> Finding:
        """Invoke the Observability Agent and return its finding.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            use_llm: Whether the observability agent should use LLM.

        Returns:
            Finding from the Observability Agent.
        """

        state_manager.timeline.add_event(
            "agent_invoked",
            "Invoking Observability Agent for telemetry analysis",
            self.name,
        )

        finding = self.observability_agent.investigate(state_manager, scenario, use_llm)

        state_manager.timeline.add_event(
            "agent_completed",
            f"Observability Agent returned finding: {finding.summary[:80]}",
            self.name,
        )

        return finding

    def _synthesize_findings(
        self,
        state_manager: InvestigationStateManager,
        scenario: dict[str, Any],
        findings: list[Finding],
        use_llm: bool,
    ) -> None:
        """Synthesize multiple agent findings into hypotheses and recommendations.

        Args:
            state_manager: Shared investigation state.
            scenario: Full scenario data.
            findings: List of findings from all agents.
            use_llm: Whether to use LLM for synthesis.
        """

        try:
            incident = state_manager.incident
            evidence = state_manager.evidence_store.get_all()

            findings_summary = "\n".join(
                f"- {f.agent}: {f.summary} (confidence={f.confidence:.2f}, hypothesis={f.hypothesis})"
                for f in findings
            )

            evidence_summary = "\n".join(
                f"- [{e.type.value}] {e.source}: {e.description} (relevance={e.relevance:.2f})"
                for e in evidence
            )

            prompt = build_finding_synthesis_prompt(
                incident_title=incident.title,
                incident_description=incident.description,
                findings_summary=findings_summary,
                evidence_summary=evidence_summary,
            )

            session = self.session_service.create_session_sync(
                app_name=self.app_name,
                user_id="incidentforge",
                state={},
            )
            runner = Runner(
                agent=self.adk_agent,
                session_service=self.session_service,
                app_name=self.app_name,
            )

            user_message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

            final_output: str | None = None
            for event in runner.run(
                user_id="incidentforge",
                session_id=session.id,
                new_message=user_message,
            ):
                if event.output is not None:
                    final_output = str(event.output)

            if final_output:
                self._apply_synthesis(state_manager, final_output)

        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            state_manager.timeline.add_event(
                "synthesis_error",
                f"Finding synthesis failed: {exc}",
                self.name,
            )

    def _apply_synthesis(
        self,
        state_manager: InvestigationStateManager,
        synthesis_output: str,
    ) -> None:
        """Apply the synthesis output to the investigation state.

        Args:
            state_manager: Shared investigation state.
            synthesis_output: JSON string from LLM synthesis.
        """

        try:
            result = json.loads(synthesis_output)

            for hyp in result.get("hypotheses", []):
                state_manager.timeline.add_event(
                    "hypothesis_proposed",
                    f"Hypothesis: {hyp.get('hypothesis', '')} (confidence={hyp.get('confidence', 0):.2f})",
                    self.name,
                )

            for rec in result.get("recommendations", []):
                from models.recommendation import Recommendation, RecommendationPriority

                priority_map = {
                    "high": RecommendationPriority.HIGH,
                    "medium": RecommendationPriority.MEDIUM,
                    "low": RecommendationPriority.LOW,
                }
                priority = priority_map.get(rec.get("priority", "medium").lower(), RecommendationPriority.MEDIUM)

                recommendation = Recommendation(
                    action=rec.get("action", ""),
                    priority=priority,
                    rationale=rec.get("rationale", ""),
                    confidence=0.8,
                )
                state_manager.add_recommendation(recommendation)

            for gap in result.get("evidence_gaps", []):
                state_manager.timeline.add_event(
                    "evidence_gap_identified",
                    f"Gap: {gap}",
                    self.name,
                )

        except (json.JSONDecodeError, KeyError) as exc:
            state_manager.timeline.add_event(
                "synthesis_parse_error",
                f"Failed to parse synthesis output: {exc}",
                self.name,
            )

    def coordinate_from_state(
        self,
        incident_state: IncidentState,
        use_llm: bool = True,
    ) -> list[Finding]:
        """Coordinate investigation from an IncidentState object.

        This is the primary callable interface for the orchestrator.

        Args:
            incident_state: Current investigation state.
            use_llm: Whether to use LLM for coordination.

        Returns:
            List of findings from all invoked specialist agents.
        """

        scenario = {
            "incident": incident_state.incident.model_dump(mode="json"),
            "logs": [],
            "metrics": {},
            "traces": {},
        }

        incident = incident_state.incident
        state_manager = InvestigationStateManager(incident)

        for finding in incident_state.investigation.findings:
            state_manager.add_finding(finding)

        return self.investigate(state_manager, scenario, use_llm)


def create_incident_commander(
    model_name: str | None = None,
    app_name: str = "incidentforge",
) -> IncidentCommander:
    """Factory function to create an Incident Commander instance.

    Args:
        model_name: Optional model override.
        app_name: Application name for ADK sessions.

    Returns:
        Configured IncidentCommander instance.
    """

    return IncidentCommander(model_name=model_name, app_name=app_name)