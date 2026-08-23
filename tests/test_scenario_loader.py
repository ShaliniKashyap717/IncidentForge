import json
from pathlib import Path

import pytest

from scripts.load_scenarios import ScenarioLoadError, load_scenario


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "payment_latency"


def test_payment_latency_scenario_loads_successfully():
    scenario = load_scenario(SCENARIO_DIR)

    assert scenario["name"] == "payment_latency"
    assert scenario["incident"]["id"] == "INC-2026-1042"
    assert scenario["incident"]["severity"] == "high"
    assert scenario["incident"]["status"] == "investigating"
    assert any(entry["service"] == "payment-api" for entry in scenario["logs"])
    assert scenario["metrics"]["anomaly"]["type"] == "latency_spike"
    assert len(scenario["traces"]["traces"]) == 3
    assert scenario["deployments"]["deployments"][0]["service"] == "payment-api"
    assert scenario["commits"]["commits"][0]["message"].startswith("Increase payment retry timeout")


def test_missing_scenario_files_produce_clear_errors(tmp_path):
    scenario_dir = tmp_path / "missing_log_file"
    scenario_dir.mkdir()
    (scenario_dir / "incident.json").write_text(
        json.dumps(
            {
                "id": "INC-1001",
                "title": "Missing telemetry",
                "description": "Test scenario missing files.",
                "severity": "medium",
                "affected_services": ["api"],
                "status": "detected",
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "metrics.json").write_text("{}", encoding="utf-8")
    (scenario_dir / "traces.json").write_text("{}", encoding="utf-8")
    (scenario_dir / "deployments.json").write_text("{}", encoding="utf-8")
    (scenario_dir / "commits.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ScenarioLoadError, match="logs.txt"):
        load_scenario(scenario_dir)
