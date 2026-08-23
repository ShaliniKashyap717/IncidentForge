"""Utilities for loading and validating scenario fixture directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.incident import Incident


class ScenarioLoadError(ValueError):
    """Raised when a scenario directory or one of its required files is invalid."""


REQUIRED_FILES = (
    "incident.json",
    "logs.txt",
    "metrics.json",
    "traces.json",
    "deployments.json",
    "commits.json",
)


def _parse_log_lines(path: Path) -> list[dict[str, str]]:
    """Parse log lines in a simple timestamp-level-service-message format."""
    entries: list[dict[str, str]] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(" ", 3)
        if len(parts) != 4:
            raise ScenarioLoadError(
                f"Malformed log entry in '{path.name}' on line {line_number}: "
                f"expected '<timestamp> <severity> <service> <message>' but got: {raw_line!r}"
            )

        timestamp, severity, service, message = parts
        entries.append(
            {
                "timestamp": timestamp,
                "severity": severity,
                "service": service,
                "message": message,
            }
        )

    return entries


def _load_json_file(path: Path, label: str) -> Any:
    """Read and parse a JSON fixture file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ScenarioLoadError(f"Missing required file for scenario: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError(f"Malformed JSON in '{label}': {exc.msg} (line {exc.lineno}, column {exc.colno})") from exc


def load_scenario(scenario_dir: str | Path) -> dict[str, Any]:
    """Load a scenario directory and return a normalized, validated structure.

    The loader reads the scenario metadata and telemetry fixtures, validates the incident
    payload using the existing Pydantic model, and returns a cleaned dictionary for the
    rest of the investigation pipeline.
    """
    scenario_path = Path(scenario_dir)
    if not scenario_path.exists():
        raise ScenarioLoadError(f"Scenario directory does not exist: '{scenario_path}'")
    if not scenario_path.is_dir():
        raise ScenarioLoadError(f"Scenario path is not a directory: '{scenario_path}'")

    missing_files = [name for name in REQUIRED_FILES if not (scenario_path / name).exists()]
    if missing_files:
        missing = ", ".join(missing_files)
        raise ScenarioLoadError(f"Missing required file(s) for scenario '{scenario_path.name}': {missing}")

    incident_path = scenario_path / "incident.json"
    logs_path = scenario_path / "logs.txt"
    metrics_path = scenario_path / "metrics.json"
    traces_path = scenario_path / "traces.json"
    deployments_path = scenario_path / "deployments.json"
    commits_path = scenario_path / "commits.json"

    try:
        incident_data = _load_json_file(incident_path, "incident.json")
        incident = Incident.model_validate(incident_data)
    except ValueError as exc:
        raise ScenarioLoadError(f"Malformed incident definition in '{incident_path.name}': {exc}") from exc

    try:
        logs = _parse_log_lines(logs_path)
    except OSError as exc:
        raise ScenarioLoadError(f"Unable to read log file '{logs_path.name}': {exc}") from exc

    metrics = _load_json_file(metrics_path, "metrics.json")
    traces = _load_json_file(traces_path, "traces.json")
    deployments = _load_json_file(deployments_path, "deployments.json")
    commits = _load_json_file(commits_path, "commits.json")

    return {
        "name": scenario_path.name,
        "incident": incident.model_dump(mode="json"),
        "logs": logs,
        "metrics": metrics,
        "traces": traces,
        "deployments": deployments,
        "commits": commits,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load a scenario fixture directory.")
    parser.add_argument("scenario_dir", help="Path to the scenario directory to load.")
    args = parser.parse_args()

    try:
        scenario = load_scenario(args.scenario_dir)
        print(json.dumps(scenario, indent=2, sort_keys=True))
    except ScenarioLoadError as exc:
        raise SystemExit(f"Error: {exc}") from exc
