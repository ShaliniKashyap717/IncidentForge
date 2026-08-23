"""Database lock and contention helpers."""

from __future__ import annotations

from typing import Any


LOCK_KEYWORDS = ("lock", "deadlock", "contention", "blocked", "waiting")


def detect_lock_signals_from_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Find lock/contention-related log entries."""

	matches: list[dict[str, Any]] = []
	for entry in logs:
		message = str(entry.get("message", "")).lower()
		if any(keyword in message for keyword in LOCK_KEYWORDS):
			matches.append(entry)
	return matches


def infer_contention_from_spans(database_spans: list[dict[str, Any]]) -> dict[str, Any]:
	"""Infer potential contention from repeated high-latency DB spans."""

	slow = [span for span in database_spans if float(span.get("duration_ms", 0.0)) >= 1500.0]
	if not slow:
		return {
			"possible_contention": False,
			"slow_span_count": 0,
			"description": "No severe database span latency indicating lock contention.",
		}

	return {
		"possible_contention": True,
		"slow_span_count": len(slow),
		"description": (
			f"{len(slow)} database spans exceeded 1500ms, which may indicate contention or lock-related delay."
		),
	}


def summarize_lock_signals(lock_logs: list[dict[str, Any]]) -> str:
	"""Summarize lock-related logs for downstream reasoning."""

	if not lock_logs:
		return "No lock-related log signals were detected."

	first = lock_logs[0]
	return (
		f"Detected {len(lock_logs)} lock/contention log signals; "
		f"example: {first.get('timestamp', 'unknown')} {first.get('service', 'unknown')} "
		f"{first.get('message', '')}"
	)
