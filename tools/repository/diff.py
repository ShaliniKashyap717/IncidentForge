"""Code diff inspection helpers."""

from __future__ import annotations

from typing import Any


def infer_change_categories_from_message(message: str) -> list[str]:
	"""Infer high-level change categories from commit/deployment text."""

	lowered = message.lower()
	categories: list[str] = []

	mapping = {
		"retry": "retry-policy",
		"backoff": "retry-policy",
		"timeout": "timeout-config",
		"config": "configuration",
		"dependency": "dependency-change",
		"performance": "performance",
		"latency": "performance",
	}

	for token, category in mapping.items():
		if token in lowered and category not in categories:
			categories.append(category)

	return categories


def compare_change_overlap(primary_text: str, secondary_text: str) -> float:
	"""Compute overlap score between two change descriptions in [0, 1]."""

	first = set(primary_text.lower().split())
	second = set(secondary_text.lower().split())
	if not first or not second:
		return 0.0
	return len(first & second) / float(max(len(first), len(second)))


def correlate_commit_and_deployment(
	commit: dict[str, Any],
	deployment: dict[str, Any],
) -> dict[str, Any]:
	"""Build a deterministic correlation object between commit and deployment metadata."""

	commit_message = str(commit.get("message", ""))
	deployment_notes = str(deployment.get("notes", ""))

	return {
		"commit_sha": commit.get("sha"),
		"deployment_id": deployment.get("id"),
		"service_match": str(deployment.get("service", "")).lower() in commit_message.lower(),
		"overlap_score": compare_change_overlap(commit_message, deployment_notes),
		"commit_categories": infer_change_categories_from_message(commit_message),
		"deployment_categories": infer_change_categories_from_message(deployment_notes),
	}
