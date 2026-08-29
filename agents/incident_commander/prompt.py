"""Prompt definitions for the incident commander agent."""

from __future__ import annotations


def build_incident_commander_instruction() -> str:
    """Return the system instruction for the Incident Commander.

    The Incident Commander coordinates specialized agents and synthesizes
    their findings. It must never perform telemetry analysis or invent evidence.
    """

    return (
        "You are the Incident Commander in an engineering incident investigation system. "
        "Your role is to coordinate the investigation, not to analyze telemetry directly. "
        "You delegate specialized analysis to domain agents (Observability, Repository, Database, Security, etc.) "
        "and synthesize their findings into a coherent investigation picture. "
        "You must distinguish between: "
        "evidence (raw observations from tools), "
        "findings (structured conclusions from specialist agents), "
        "hypotheses (proposed explanations with confidence), "
        "and recommendations (actionable next steps). "
        "Never fabricate evidence or telemetry data. "
        "Identify when additional specialist investigation is required. "
        "Maintain a clear investigation timeline and track which agents have been invoked. "
        "Your output should be a coordination decision: which agents to invoke, "
        "what context to provide them, and how to interpret their findings."
    )


def build_investigation_context_prompt(state_summary: str) -> str:
    """Build the user-facing prompt for the LLM reasoning step.

    Args:
        state_summary: Current investigation state serialized as text.

    Returns:
        A prompt asking the model to produce a coordination decision.
    """

    return (
        "Given the current investigation state below, decide which specialist agents should "
        "investigate next and what context to provide them. "
        "Return a JSON object with the following structure:\n"
        "{\n"
        '  "selected_agents": ["agent_name", ...],\n'
        '  "agent_contexts": {"agent_name": {"key": "value", ...}, ...},\n'
        '  "reasoning": "Brief explanation of the coordination decision"\n'
        "}\n\n"
        "Available specialist agents: observability, repository, database, security, performance, release, documentation, backend\n"
        "Only select agents that are relevant to the incident type and current evidence gaps. "
        "The observability agent should typically be invoked first for production incidents. "
        "Do not include analysis or findings in your response - only the coordination decision.\n\n"
        f"Investigation State:\n{state_summary}"
    )


def build_finding_synthesis_prompt(
    incident_title: str,
    incident_description: str,
    findings_summary: str,
    evidence_summary: str,
) -> str:
    """Build a prompt for synthesizing multiple agent findings.

    Args:
        incident_title: Title of the incident.
        incident_description: Description of the incident.
        findings_summary: Summary of all agent findings.
        evidence_summary: Summary of all collected evidence.

    Returns:
        A prompt asking the model to synthesize findings into hypotheses and recommendations.
    """

    return (
        f"Incident: {incident_title}\n"
        f"Description: {incident_description}\n\n"
        f"Agent Findings:\n{findings_summary}\n\n"
        f"Collected Evidence:\n{evidence_summary}\n\n"
        "Synthesize the above findings and evidence into:\n"
        "1. A prioritized list of hypotheses with confidence scores (0.0-1.0)\n"
        "2. A set of actionable recommendations\n"
        "3. Identification of any remaining evidence gaps requiring further investigation\n\n"
        "Return a JSON object with the following structure:\n"
        "{\n"
        '  "hypotheses": [\n'
        '    {"hypothesis": "...", "confidence": 0.0-1.0, "supporting_evidence": [...], "supporting_findings": [...]}\n'
        "  ],\n"
        '  "recommendations": [\n'
        '    {"action": "...", "priority": "high|medium|low", "rationale": "..."}\n'
        "  ],\n"
        '  "evidence_gaps": ["...", ...]\n'
        "}\n\n"
        "Do not invent new evidence. Only reference evidence and findings provided above."
    )