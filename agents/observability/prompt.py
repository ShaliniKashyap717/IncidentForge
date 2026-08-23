"""Prompt definitions for the observability agent."""

from __future__ import annotations


def build_observability_instruction() -> str:
	"""Return the system instruction for the Observability Agent.

	The instruction keeps reasoning focused on evidence-backed telemetry analysis
	and explicitly separates observations from hypotheses and recommendations.
	"""

	return (
		"You are the Observability Agent in an engineering incident investigation system. "
		"You analyze structured outputs from deterministic telemetry tools for logs, metrics, and traces. "
		"Your job is to identify anomalies, correlate telemetry signals, formulate hypotheses, assign confidence, "
		"and provide evidence-backed next actions. "
		"You must never invent evidence. "
		"Distinguish observations from hypotheses and recommendations. "
		"Return a structured Finding that includes actual evidence items from the provided evidence pool."
	)


def build_finding_generation_prompt(analysis_payload: str) -> str:
	"""Build the user-facing prompt for the LLM reasoning step.

	Args:
		analysis_payload: Structured telemetry analysis serialized as JSON.

	Returns:
		A concise prompt asking the model to produce a structured Finding.
	"""

	return (
		"Using the following structured telemetry analysis, produce a single structured Finding JSON "
		"that matches the IncidentForge Finding model. "
		"Use only the evidence that appears in the provided evidence pool. "
		"Do not invent new evidence. "
		"Return only the Finding content.\n\n"
		f"{analysis_payload}"
	)
