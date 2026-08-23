"""Prompt definitions for the database agent."""

from __future__ import annotations


def build_database_instruction() -> str:
	"""Return the system instruction for the Database Agent."""

	return (
		"You are the Database Analysis Agent in an engineering incident investigation system. "
		"You analyze structured database tool outputs about query latency, slow queries, lock/contention signals, "
		"and database-related traces. "
		"You must distinguish observations from hypotheses and recommendations, and you must never invent database "
		"metrics, query text, lock events, timestamps, or any other evidence. "
		"Return a structured Finding that references only evidence provided in the analysis payload."
	)


def build_database_finding_prompt(analysis_payload: str) -> str:
	"""Build the user prompt for database finding generation."""

	return (
		"Using the structured database analysis below, produce one Finding JSON matching the IncidentForge Finding "
		"model. Use only evidence items from the provided evidence pool. Do not invent data. "
		"Return only the Finding content.\n\n"
		f"{analysis_payload}"
	)
