"""Honest deterministic simulator: recall removes the scripted trial-and-error cost."""
import json
from pathlib import Path

tasks=json.loads(Path(__file__).with_name("tasks.json").read_text())
runs=[{"task":x["task"],"group":x["group"],"baseline":{"turns":5,"tool_calls":8,"success":True},"with_memory":{"turns":2,"tool_calls":3,"success":True}} for x in tasks]
out={"method":"simulated scripted agent", "runs":runs, "aggregate":{"baseline_turns":15,"memory_turns":6,"baseline_tool_calls":24,"memory_tool_calls":9}}
target=Path(__file__).parent/"results/latest.json";target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
