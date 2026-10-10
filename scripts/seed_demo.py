"""Seed canonical sample traces via the shared service."""
import json
from pathlib import Path
from meg.service import MegService
from meg.db import FalkorStore
s=MegService(FalkorStore())
for trace in Path("sample_traces").glob("*.json"): print(s.record(json.loads(trace.read_text())))
