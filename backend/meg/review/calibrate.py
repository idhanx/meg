"""Offline reviewer calibration; scores below the floor are disabled by gates."""
from __future__ import annotations
import json
from pathlib import Path
def calibration_score(predicted:list[str],expected:list[str])->float:
    return sum(a==b for a,b in zip(predicted,expected))/max(1,len(expected))
def labelled_traces()->list[dict]:
    return json.loads((Path(__file__).parents[3]/"data/labelled_traces.json").read_text())
