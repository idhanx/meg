# Three-minute demo

Start `docker compose up`, then run `python scripts/seed_demo.py` and
`python scripts/demo_flow.py`. Open the UI at port 5173, recall a CI fix, and
show its highlighted graph path. Use a readonly agent to demonstrate a denied
restricted procedure and its audit edge.

MCP stdio registration: `uv run python -m meg.mcp_server`.
