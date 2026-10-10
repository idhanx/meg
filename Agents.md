# AGENTS.md —meg build spec

You are building **meg** for the WeMakeDevs x FalkorDB hackathon (Graph Hacks), **Track 02: Agent Memory and Coordination**. Read this whole file before writing code. Work milestone by milestone, keep the app runnable at every step, and commit after each milestone.

## Build status

- [x] M1 Core store
- [x] M2 Ingest
- [x] M3 Recall
- [x] M4 API + MCP
- [x] M5 Governance
- [ ] M6 UI
- [ ] M7 Benchmark + demo
- [ ] M8 Ship

## 1. What meg is

A shared, governed procedural memory for AI coding agents, stored in FalkorDB.

- When an agent finishes a task,meg saves the steps that worked as a graph.
- The next agent that gets a similar task recalls that procedure and skips the trial and error.
- A governance layer decides which agents may read or write which procedures, and logs every access as an edge in the graph.
- A web UI shows the graph, the path behind each recall, the audit log, and benchmark results.

## 2. Hard constraints (hackathon rules)

1. **FalkorDB is the primary and central database.** All procedures, steps, policies, and audit records live in FalkorDB. No Postgres, no SQLite for core data, no other graph or vector DB.
2. All FalkorDB-related code must be new work written during the event. Do not copy an existing graph layer.
3. Third-party libraries are fine, but the graph logic (schema, ingest merge, recall ranking, governance, audit) must be our own code.
4. Must run locally with `docker compose up` plus a few commands. A live deployment is a bonus, not a requirement.
5. Deliverables: working repo, README with setup steps, demo script, benchmark results, architecture diagram.

## 3. Stack

- Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- `falkordb` Python client (`from falkordb import FalkorDB`; `db.select_graph(name)`; `graph.query(cypher, params)`)
- `mcp` Python SDK (`from mcp.server.fastmcp import FastMCP`) for the MCP server
- Embeddings: `sentence-transformers` with `all-MiniLM-L6-v2` (384 dims). Must be optional: if the model can't load, fall back to keyword matching so the app still works.
- Frontend: React + Vite + TypeScript, `react-force-graph-2d` (or `cytoscape`) for graph drawing
- Tests: `pytest`, `httpx`
- Infra: Docker Compose (FalkorDB + API + UI)

Verify FalkorDB syntax (vector indexes, procedures like `db.idx.vector.queryNodes`) against the official FalkorDB docs before relying on it. If a feature behaves differently than described here, adapt and note it in `docs/NOTES.md`.

## 4. Repo layout

```
meg/
├── AGENTS.md
├── README.md
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── docs/
│   ├── NOTES.md
│   ├── ARCHITECTURE.md
│   └── DEMO.md
├── backend/
│   └── meg/
│       ├── config.py
│       ├── db.py              # FalkorDB connection, graph-per-tenant helper
│       ├── schema.py          # indexes + constraints per tenant graph
│       ├── models.py          # Pydantic models
│       ├── ingest/
│       │   ├── parser.py      # raw trace -> normalized Trace
│       │   ├── distill.py     # drop dead ends, keep verified path
│       │   └── merge.py       # prefix merge into existing procedures
│       ├── recall/
│       │   ├── embed.py
│       │   ├── search.py      # candidate retrieval
│       │   └── rank.py        # Cypher re-ranking + chaining
│       ├── governance/
│       │   ├── policy.py      # policy evaluation
│       │   └── audit.py       # ACCESSED edges
│       ├── api.py             # FastAPI app
│       └── mcp_server.py      # MCP tools
├── tests/
├── bench/
│   ├── tasks.json             # benchmark task set
│   ├── run_bench.py
│   └── results/
├── scripts/
│   ├── seed_demo.py
│   └── demo_flow.py
├── sample_traces/             # 8-10 realistic agent sessions (JSON)
└── ui/                        # React app
```

## 5. Data model (FalkorDB)

One graph per tenant, named `tenant:<tenant_id>`. Isolation comes from graph separation.

### Nodes

| Label     | Key properties                                                                                                                                                                                |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent     | `id`, `name`, `role`                                                                                                                                                                    |
| Task      | `id`, `description`, `embedding` (vecf32), `created_at`                                                                                                                               |
| Procedure | `id`, `title`, `summary`, `embedding`, `sensitivity` (`public`/`internal`/`restricted`), `owner_agent`, `success_count`, `fail_count`, `created_at`, `last_used_at` |
| Step      | `id`, `signature` (normalized hash), `kind` (`edit`/`command`/`read`/`search`/`other`), `description`, `command`, `order`                                               |
| File      | `path`                                                                                                                                                                                      |
| Command   | `text`, `expected_exit`                                                                                                                                                                   |
| Policy    | `id`, `name`, `effect` (`allow`/`deny`), `action` (`read`/`write`), `agent_role`, `max_sensitivity`                                                                       |

### Relationships

- `(Procedure)-[:SOLVES]->(Task)`
- `(Procedure)-[:HAS_STEP {order}]->(Step)`
- `(Step)-[:NEXT]->(Step)`
- `(Step)-[:TOUCHES]->(File)`
- `(Procedure)-[:VERIFIED_BY]->(Command)`
- `(Agent)-[:RECORDED]->(Procedure)`
- `(Agent)-[:ACCESSED {action, decision, reason, ts, query}]->(Procedure)`
- `(Policy)-[:GOVERNS]->(Procedure)` (optional per-procedure override)
- `(Procedure)-[:BUILDS_ON]->(Procedure)` (set when a recorded procedure shares a prefix with or extends another)

Steps are shared nodes: identical steps (same `signature`) across procedures are the same node. That is what makes prefix merging and graph traversal meaningful.

### Indexes (create in `schema.py`, idempotent)

- Range indexes on `Procedure.id`, `Step.signature`, `Agent.id`, `File.path`
- Vector index on `Procedure.embedding` and `Task.embedding` (dimension 384, cosine). Check the docs for exact syntax.

## 6. Trace format (input to `record`)

```json
{
  "tenant_id": "demo",
  "agent": { "id": "agent-a", "name": "Agent A", "role": "developer" },
  "task": "Fix failing pytest caused by missing env var in CI",
  "sensitivity": "internal",
  "events": [
    { "type": "read", "path": "ci.yml" },
    { "type": "command", "text": "pytest -x", "exit_code": 1 },
    {
      "type": "edit",
      "path": ".github/workflows/ci.yml",
      "summary": "add API_KEY env"
    },
    { "type": "command", "text": "pytest -x", "exit_code": 0 }
  ],
  "outcome": "success"
}
```

Also write a parser that can ingest Claude Code JSONL session logs (best-effort): map tool calls to events (`Read`, `Edit`/`Write`, `Bash`, `Grep`), and use the Bash exit status when present. Keep this behind `parser.py`; the JSON format above is the canonical form.

## 7. Ingest pipeline

1. **Normalize** events into `Step` candidates. Compute `signature = sha1(kind + normalized_command_or_path_pattern)`. Normalize by stripping absolute paths, numbers, hashes, and timestamps so equivalent steps collapse.
2. **Distill**: find the final verified success (last command with exit 0 after any failure). Remove steps that only belong to failed branches (for example, an edit that was later reverted, or a command that failed and was not followed by a relevant fix). Keep the shortest path that leads from start to the verified success. Document the rule in `distill.py`.
3. **Merge**:
   - MERGE `Step` nodes by `signature`.
   - If the new step sequence shares a prefix of 2+ steps with an existing procedure, link the new procedure with `BUILDS_ON` to it, and reuse the shared step nodes.
   - If the sequence is identical to an existing procedure, do not duplicate; increment `success_count` and update `last_used_at`.
4. **Write**: Procedure, Task (with embedding), Steps, File and Command nodes, `RECORDED`, `SOLVES`, `HAS_STEP`, `NEXT`, `TOUCHES`, `VERIFIED_BY`.
5. Run the write in a way that doesn't leave partial procedures on failure (build all queries first, execute together, handle errors).
6. Failed traces (`outcome: "failure"`) are stored only as increments to `fail_count` on a matching procedure if one exists; otherwise ignored.

## 8. Recall engine

`recall(tenant_id, agent_id, task_text, k=3)`:

1. Embed the task. Retrieve top 10 candidate procedures via vector search on `Procedure.embedding` and `Task.embedding`. Fallback: keyword overlap over `title`/`summary`/`Task.description`.
2. **Governance filter** (section 9) removes procedures the agent may not read. Log a `denied` ACCESSED edge for each blocked candidate.
3. **Re-rank** the allowed candidates with this score (weights in `config.py`):

   `score = 0.55 * similarity + 0.20 * success_rate + 0.15 * recency + 0.10 * path_overlap`

   - `success_rate = success_count / (success_count + fail_count + 1)`
   - `recency` = exponential decay on `last_used_at`
   - `path_overlap` = share of the candidate's `File` nodes that appear in the files mentioned in `task_text`
4. **Chaining**: if the best single match covers less than ~60% of the task keywords, try to find a second procedure linked via `BUILDS_ON` or sharing File nodes, and return an ordered chain with a note on any uncovered part.
5. Return the top results, each with: `procedure_id`, `title`, `score`, `score_breakdown`, `steps` (ordered), `files`, `verify_command`, `why` (human-readable reason), and `path` (node ids for the UI to highlight).
6. Log an `allowed` ACCESSED edge for each returned procedure and update `last_used_at`.

## 9. Governance layer

- Sensitivity order: `public` < `internal` < `restricted`.
- A Policy matches on `agent_role`, `action`, and `max_sensitivity`. Default policy set seeded per tenant:
  - role `developer`: read/write up to `internal`
  - role `intern`: read up to `internal`, write none
  - role `security`: read/write up to `restricted`
  - role `readonly`: read `public` only
- Default is **deny** if no policy matches.
- A per-procedure `GOVERNS` policy overrides the role policies.
- Every decision (allow or deny) writes an `ACCESSED` edge with `action`, `decision`, `reason`, `ts`, `query`.
- Expose `GET /audit` with filters (agent, procedure, decision, time range) backed by Cypher over `ACCESSED` edges.
- `record` is also gated: a denied write is logged and returns 403.

## 10. API (FastAPI)

All routes take `tenant_id` (query or body). Return JSON.

- `POST /record` — body: trace. Returns `{procedure_id, merged_into, new_steps, reused_steps}`
- `POST /recall` — body: `{tenant_id, agent_id, task, k}`. Returns ranked procedures with `why` and `path`
- `GET /procedures/{id}/explain` — score breakdown, steps, who recorded it, access history
- `GET /graph` — nodes and edges for the UI (`?tenant_id=&focus=<procedure_id>`)
- `GET /audit` — audit log with filters
- `GET /policies`, `POST /policies` — list and create policies
- `GET /bench/results` — latest benchmark JSON
- `GET /health`

## 11. MCP server

Using FastMCP, expose:

- `record(trace_json)` — save a procedure from a finished session
- `recall(task, agent_id, tenant_id="default")` — find relevant procedures
- `explain(procedure_id)` — why a procedure was chosen and its history

The MCP server calls the same service functions as the API (no logic duplication). Provide a `docs/` snippet showing how to register it in Claude Code / Codex config (stdio transport).

## 12. Web UI

Pages:

1. **Graph**: force-directed graph of the tenant's procedures, steps, and files. Search box runs `recall` and highlights the returned path in a contrasting color. Click a node to see details.
2. **Recall**: pick an agent, type a task, see ranked results with the score breakdown and the `why` text.
3. **Audit**: table of allowed and denied accesses with filters; denied rows clearly marked.
4. **Benchmark**: chart of turns and tool calls with vs. without memory, per task and in aggregate.

Keep the UI simple and clean. Priority order if time is short: Graph (highlight path) > Audit > Benchmark > Recall.

## 13. Benchmark

- `bench/tasks.json`: 10 tasks in 3 groups: exact repeat, similar variation, and a chained task.
- `run_bench.py` runs each task two ways: baseline (no memory, scripted agent simulator tries steps with a fixed trial-and-error cost model) and with ProcGraph recall. Record **turns**, **tool calls**, and **success** per run.
- Be honest: if using a simulated agent, label the benchmark as simulated in the README and UI. If a real agent run is feasible (Codex or Claude Code on small repos), prefer that and report variance.
- Write results to `bench/results/latest.json`.

## 14. Demo data and script

- `scripts/seed_demo.py`: creates tenant `demo`, default policies, three agents (`agent-a` developer, `agent-b` developer, `agent-c` readonly), and ingests everything in `sample_traces/`.
- `sample_traces/` must include at least: a CI env-var fix, a failing-import fix, a dependency version pin, a Docker build fix, a DB migration fix, plus two traces that share a 2+ step prefix so merging is visible, and one `restricted` procedure.
- `scripts/demo_flow.py` prints the 3-minute demo:
  1. Agent A records a procedure.
  2. Agent B recalls it for a similar task.
  3. The UI highlights the path.
  4. Agent C is blocked from the restricted procedure and the audit shows it.
  5. Benchmark numbers.

## 15. Configuration

`.env.example`:

```
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDINGS_ENABLED=true
API_PORT=8000
DEFAULT_TENANT=demo
```

`docker-compose.yml` services: `falkordb` (image `falkordb/falkordb:latest`, port 6379, optional browser port 3000), `api`, `ui`.

## 16. Milestones

Do them in order. Each ends with passing tests and a runnable app.

1. **M1 Core store**: Compose + FalkorDB connection, per-tenant graph helper, schema/indexes, Pydantic models. Test: create tenant, run schema twice (idempotent).
2. **M2 Ingest**: parser, distill, merge, write. Test: ingest two traces with a shared prefix and assert shared Step nodes and a `BUILDS_ON` edge; ingest an identical trace and assert no duplicate.
3. **M3 Recall**: embeddings (with fallback), search, rank, explain. Test: similar task returns the right procedure first; `why` and `path` present.
4. **M4 API + MCP**: all routes and the three MCP tools sharing one service layer. Test with `httpx`.
5. **M5 Governance**: policies, filter, ACCESSED edges, `/audit`, gated `record`. Test: readonly agent is denied a restricted procedure and the denial is in the audit log.
6. **M6 UI**: Graph (with highlighted recall path), Audit, Recall, Benchmark pages.
7. **M7 Benchmark + demo**: bench runner, seed, demo flow script, results shown in UI.
8. **M8 Ship**: README, architecture doc, demo video script, cleanup, final run-through from a clean clone.

## 17. Acceptance criteria (definition of done)

- `docker compose up` then `python scripts/seed_demo.py` gives a working demo with no manual steps.
- `record` and `recall` work through both the REST API and the MCP server.
- Recording two traces with a shared prefix reuses Step nodes and creates `BUILDS_ON`.
- `recall` returns ranked results with a score breakdown, a `why` text, and a node path the UI highlights.
- A restricted procedure is invisible to the readonly agent, and the denial appears in `/audit` and the UI.
- Per-tenant graph isolation: a recall in tenant `a` never returns tenant `b` data (tested).
- Benchmark results exist and are displayed, clearly labeled simulated or real.
- All tests pass; README setup works from a clean clone.

## 18. Coding rules

- Use parameterized Cypher (`graph.query(q, params)`). Never build queries by string-formatting user input. Tenant names must be validated against `^[a-z0-9_-]+$`.
- Keep Cypher in one place per module with clear names; add a short comment explaining each non-trivial query.
- Type hints everywhere, small functions, no dead code.
- Don't hardcode secrets; read config from env.
- If something in this spec conflicts with FalkorDB's actual behavior, follow the real behavior and record the deviation in `docs/NOTES.md`.
- Don't add features outside this spec until every acceptance criterion passes.

## 19. Cut list (if time runs short, drop in this order)

1. UI polish and the Recall page
2. Chained procedure plans (keep single-procedure recall)
3. Claude Code JSONL parser (keep the canonical JSON format)
4. Real-agent benchmark (keep the simulated one, labeled)

**Never cut:** FalkorDB graph logic, prefix merge, governance with audit edges, the MCP tools, the highlighted-path graph view, and the benchmark.
