"""Log analysis helpers for observability tooling."""

from __future__ import annotations

from typing import Callable


def search_logs(
    logs: list[dict[str, str]],
    query: str | None = None,
    service: str | None = None,
    severity: str | None = None,
) -> list[dict[str, str]]:
    """Search and filter logs by query string, service, and severity level.

    Args:
        logs: List of log entry dictionaries with at least 'message', 'service', 'severity' keys.
        query: Substring to match in the log message (case-insensitive).
        service: Filter logs to a specific service name.
        severity: Filter logs to a specific severity level (e.g., 'ERROR', 'WARN').

    Returns:
        Filtered list of log entries matching all provided criteria.
    """
    results = logs

    if service:
        results = [entry for entry in results if entry.get("service", "").lower() == service.lower()]

    if severity:
        results = [entry for entry in results if entry.get("severity", "").upper() == severity.upper()]

    if query:
        query_lower = query.lower()
        results = [
            entry
            for entry in results
            if query_lower in entry.get("message", "").lower()
        ]

    return results


def count_errors(
    logs: list[dict[str, str]],
    service: str | None = None,
) -> dict[str, int]:
    """Count error entries by severity level, optionally filtered by service.

    Args:
        logs: List of log entry dictionaries.
        service: Optional filter to count errors for a specific service.

    Returns:
        Dictionary mapping severity levels to error counts.
    """
    if service:
        logs = [entry for entry in logs if entry.get("service", "").lower() == service.lower()]

    error_counts: dict[str, int] = {}
    for entry in logs:
        severity = entry.get("severity", "INFO").upper()
        if severity in ("ERROR", "CRITICAL", "WARN"):
            error_counts[severity] = error_counts.get(severity, 0) + 1

    return error_counts


def summarize_events(
    logs: list[dict[str, str]],
    predicate: Callable[[dict[str, str]], bool] | None = None,
) -> list[str]:
    """Summarize important log events, optionally filtered by a predicate.

    Args:
        logs: List of log entry dictionaries.
        predicate: Optional function to filter entries (e.g., lambda e: e.get('severity') == 'ERROR').

    Returns:
        List of summarized event strings in format "timestamp [service] message".
    """
    if predicate:
        logs = [entry for entry in logs if predicate(entry)]

    summaries = []
    for entry in logs:
        timestamp = entry.get("timestamp", "unknown")
        service = entry.get("service", "unknown")
        message = entry.get("message", "")
        summaries.append(f"{timestamp} [{service}] {message}")

    return summaries
