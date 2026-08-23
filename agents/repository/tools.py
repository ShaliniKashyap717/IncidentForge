"""Tool bindings for the repository/deployment analysis agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from google.adk.tools import FunctionTool

from tools.repository.commits import (
    extract_commit_signals,
    filter_commits_by_service,
    list_commits,
    search_commits_by_keywords,
    summarize_commit,
)
from tools.repository.deployments import (
    filter_deployments_by_services,
    find_deployments_near_time,
    list_deployments,
    sort_deployments_by_timestamp,
    summarize_deployment,
)
from tools.repository.diff import correlate_commit_and_deployment
from tools.repository.search import search_any_keyword


CHANGE_KEYWORDS = [
    "retry",
    "timeout",
    "backoff",
    "dependency",
    "config",
    "performance",
    "latency",
]


def analyze_repository_commits(
    commits_payload: dict[str, Any],
    affected_services: list[str] | None = None,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Analyze commit metadata using deterministic repository tools."""

    all_commits = list_commits(commits_payload)
    scoped_commits = filter_commits_by_service(commits_payload, affected_services)
    target_keywords = keywords or CHANGE_KEYWORDS
    relevant_commits = search_commits_by_keywords(scoped_commits or all_commits, target_keywords)

    return {
        "service": commits_payload.get("service"),
        "all_commits": all_commits,
        "scoped_commits": scoped_commits,
        "relevant_commits": relevant_commits,
        "keyword_hits": [
            {
                "sha": commit.get("sha"),
                "signals": extract_commit_signals(commit),
                "summary": summarize_commit(commit),
            }
            for commit in relevant_commits
        ],
        "relevant_count": len(relevant_commits),
    }


def analyze_repository_deployments(
    deployments_payload: dict[str, Any],
    affected_services: list[str] | None = None,
    reference_timestamp: str | None = None,
    max_minutes: int = 120,
) -> dict[str, Any]:
    """Analyze deployment metadata with service and temporal correlation."""

    all_deployments = list_deployments(deployments_payload)
    scoped_deployments = filter_deployments_by_services(all_deployments, affected_services)
    sorted_deployments = sort_deployments_by_timestamp(scoped_deployments or all_deployments)

    nearby_deployments = (
        find_deployments_near_time(sorted_deployments, reference_timestamp, max_minutes=max_minutes)
        if reference_timestamp
        else []
    )

    keyword_matched = search_any_keyword(
        sorted_deployments,
        fields=["notes", "service", "status", "version"],
        keywords=CHANGE_KEYWORDS,
    )

    return {
        "all_deployments": all_deployments,
        "scoped_deployments": scoped_deployments,
        "sorted_deployments": sorted_deployments,
        "nearby_deployments": nearby_deployments,
        "keyword_matched": keyword_matched,
        "deployment_summaries": [summarize_deployment(deployment) for deployment in sorted_deployments],
    }


def analyze_repository_change_correlation(
    commits_result: dict[str, Any],
    deployments_result: dict[str, Any],
) -> dict[str, Any]:
    """Correlate relevant commits and deployments using deterministic overlap logic."""

    relevant_commits = commits_result.get("relevant_commits", [])
    candidate_deployments = deployments_result.get("nearby_deployments") or deployments_result.get("keyword_matched", [])

    correlations: list[dict[str, Any]] = []
    for commit in relevant_commits:
        for deployment in candidate_deployments:
            correlations.append(correlate_commit_and_deployment(commit, deployment))

    correlations = sorted(correlations, key=lambda entry: float(entry.get("overlap_score", 0.0)), reverse=True)

    return {
        "correlations": correlations,
        "correlation_count": len(correlations),
    }


def infer_incident_reference_timestamp(scenario: dict[str, Any]) -> str | None:
    """Infer an incident reference timestamp from telemetry/log context."""

    logs = scenario.get("logs", [])
    if isinstance(logs, list) and logs:
        first_log = logs[0]
        value = first_log.get("timestamp")
        if isinstance(value, str) and value:
            return value

    metrics = scenario.get("metrics", {})
    series = metrics.get("series", []) if isinstance(metrics, dict) else []
    if isinstance(series, list) and series:
        value = series[0].get("timestamp")
        if isinstance(value, str) and value:
            return value

    return None


def build_repository_tools() -> list[FunctionTool]:
    """Build ADK function tools for repository and deployment analysis."""

    return [
        FunctionTool(analyze_repository_commits),
        FunctionTool(analyze_repository_deployments),
        FunctionTool(analyze_repository_change_correlation),
    ]
