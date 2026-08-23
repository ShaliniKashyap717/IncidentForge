"""Deployment metadata helpers for repository analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def list_deployments(deployments_payload: dict[str, Any]) -> list[dict[str, Any]]:
	"""Return normalized deployment entries from a scenario payload."""

	deployments = deployments_payload.get("deployments", [])
	if not isinstance(deployments, list):
		raise TypeError("deployments payload must contain a list under 'deployments'.")
	return [entry for entry in deployments if isinstance(entry, dict)]


def filter_deployments_by_services(
	deployments: list[dict[str, Any]],
	affected_services: list[str] | None,
) -> list[dict[str, Any]]:
	"""Filter deployments by affected services."""

	if not affected_services:
		return deployments
	affected = {service.lower() for service in affected_services}
	return [d for d in deployments if str(d.get("service", "")).lower() in affected]


def sort_deployments_by_timestamp(
	deployments: list[dict[str, Any]],
	descending: bool = True,
) -> list[dict[str, Any]]:
	"""Sort deployments by timestamp, keeping malformed timestamps last."""

	def parse_timestamp(value: str) -> datetime | None:
		try:
			return datetime.fromisoformat(value.replace("Z", "+00:00"))
		except Exception:
			return None

	return sorted(
		deployments,
		key=lambda entry: parse_timestamp(str(entry.get("timestamp", ""))) or datetime.min,
		reverse=descending,
	)


def find_deployments_near_time(
	deployments: list[dict[str, Any]],
	reference_timestamp: str,
	max_minutes: int = 60,
) -> list[dict[str, Any]]:
	"""Find deployments within a configured window around a reference time."""

	try:
		reference = datetime.fromisoformat(reference_timestamp.replace("Z", "+00:00"))
	except Exception:
		return []

	matches: list[dict[str, Any]] = []
	for deployment in deployments:
		value = str(deployment.get("timestamp", ""))
		try:
			timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
		except Exception:
			continue

		delta_minutes = abs((reference - timestamp).total_seconds()) / 60.0
		if delta_minutes <= max_minutes:
			matches.append(deployment)

	return sort_deployments_by_timestamp(matches)


def summarize_deployment(deployment: dict[str, Any]) -> str:
	"""Return a concise textual summary of a deployment."""

	deployment_id = str(deployment.get("id", "unknown"))
	service = str(deployment.get("service", "unknown"))
	timestamp = str(deployment.get("timestamp", "unknown"))
	notes = str(deployment.get("notes", ""))
	return f"{deployment_id} for {service} at {timestamp}: {notes}"
