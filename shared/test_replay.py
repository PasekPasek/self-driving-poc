"""Checks for the replay validator and the sample fixture. Run: pytest shared/test_replay.py"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from validate_replay import validate

HERE = Path(__file__).parent
FIXTURE = HERE.parent / "fixtures" / "replay.sample.json"


def test_fixture_passes_validator_cli():
    result = subprocess.run([sys.executable, str(HERE / "validate_replay.py"), str(FIXTURE)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_fixture_covers_required_cases():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cars = [c for g in data["generations"] for c in g["cars"]]
    assert len(data["generations"]) == 2 and all(len(g["cars"]) == 3 for g in data["generations"])
    assert any(c["crashed"] for c in cars)
    assert any(0.3 < c["progress"] < 1.0 for c in cars)
    assert data["generations"][1]["completedLap"] is True
    done = [c for c in data["generations"][1]["cars"] if c["progress"] == 1.0][0]
    assert done["crashed"] is False and done["crash"] is None and "sensors" in done


def _mutated(tmp_path, mutate) -> list[str]:
    data = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))
    mutate(data)
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return validate(path)


@pytest.mark.parametrize("name, mutate", [
    ("crash not last frame", lambda d: d["generations"][0]["cars"][0]["crash"].update(frame=0)),
    ("completed but crashed", lambda d: d["generations"][1]["cars"][0].update(crashed=True)),
    ("progress disagrees with frames", lambda d: d["generations"][0]["cars"][1].update(progress=0.9)),
    ("wrong best car", lambda d: d["generations"][1].update(bestCarIndex=1)),
    ("heading not wrapped", lambda d: d["generations"][0]["cars"][0]["frames"][1].__setitem__(2, 4.0)),
    ("extras on non-best car", lambda d: d["generations"][0]["cars"][0].update(sensors=[], outputs=[])),
    ("bad rounding", lambda d: d["generations"][0]["cars"][0]["frames"][1].__setitem__(0, 171.23)),
    ("sensor out of range", lambda d: d["generations"][1]["cars"][0]["sensors"][0].__setitem__(0, 1.5)),
])
def test_validator_rejects(tmp_path, name, mutate):
    assert _mutated(tmp_path, mutate), name


def test_validator_rejects_non_compact_json(tmp_path):
    path = tmp_path / "replay.json"
    path.write_text(json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8")), indent=1),
                    encoding="utf-8")
    assert any("separators" in e for e in validate(path))
