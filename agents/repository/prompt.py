"""Prompt definitions for the repository/deployment analysis agent."""

from __future__ import annotations


def build_repository_instruction() -> str:
    """Return the system instruction for the Repository Agent."""

    return (
        "You are the Repository/Deployment Analysis Agent in an engineering incident investigation system. "
        "You specialize in analyzing structured commit and deployment metadata. "
        "You must correlate recent code/configuration changes with the incident context, identify likely change-related risks, "
        "form hypotheses, assign confidence, and provide evidence-backed next actions. "
        "You must never invent commits, deployment ids, SHAs, timestamps, or evidence. "
        "Distinguish observations from hypotheses and recommendations. "
        "Return a structured Finding that references only the evidence provided in the analysis payload."
    )


def build_repository_finding_prompt(analysis_payload: str) -> str:
    """Build the user prompt for repository finding generation."""

    return (
        "Using the following structured repository and deployment analysis, produce a single Finding JSON "
        "matching the IncidentForge Finding model. "
        "Use only evidence from the provided evidence pool. "
        "Do not invent any commit, deployment, or timestamp. "
        "Return only the Finding content.\n\n"
        f"{analysis_payload}"
    )
