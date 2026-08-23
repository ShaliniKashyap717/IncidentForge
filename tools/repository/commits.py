"""Repository commit inspection helpers."""

from __future__ import annotations

from typing import Any


CHANGE_KEYWORDS = (
	"retry",
	"timeout",
	"backoff",
	"latency",
	"performance",
	"dependency",
	"config",
)


def list_commits(commits_payload: dict[str, Any]) -> list[dict[str, Any]]:
	"""Return normalized commit entries from a scenario payload."""

	commits = commits_payload.get("commits", [])
	if not isinstance(commits, list):
		raise TypeError("commits payload must contain a list under 'commits'.")
	return [entry for entry in commits if isinstance(entry, dict)]


def filter_commits_by_service(
	commits_payload: dict[str, Any],
	affected_services: list[str] | None,
) -> list[dict[str, Any]]:
	"""Filter commits for affected services.

	The current scenario commit payload contains a single service label at the
	root, so this function uses that label and falls back safely when absent.
	"""

	commits = list_commits(commits_payload)
	if not affected_services:
		return commits

	service = str(commits_payload.get("service", "")).lower()
	if service and service in {name.lower() for name in affected_services}:
		return commits
	return []


def search_commits_by_keywords(
	commits: list[dict[str, Any]],
	keywords: list[str] | tuple[str, ...] = CHANGE_KEYWORDS,
) -> list[dict[str, Any]]:
	"""Return commits whose messages match change-related keywords."""

	lowered = [keyword.lower() for keyword in keywords]
	results: list[dict[str, Any]] = []

	for commit in commits:
		message = str(commit.get("message", "")).lower()
		if any(keyword in message for keyword in lowered):
			results.append(commit)
	return results


def extract_commit_signals(commit: dict[str, Any]) -> list[str]:
	"""Extract change signals from a commit message."""

	message = str(commit.get("message", "")).lower()
	signals: list[str] = []
	for keyword in CHANGE_KEYWORDS:
		if keyword in message:
			signals.append(keyword)
	return signals


def summarize_commit(commit: dict[str, Any]) -> str:
	"""Return a concise textual summary of a commit."""

	sha = str(commit.get("sha", "unknown"))
	author = str(commit.get("author", "unknown"))
	message = str(commit.get("message", ""))
	return f"{sha} by {author}: {message}"
