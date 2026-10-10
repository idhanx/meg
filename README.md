# meg — Memory Enhanced Graph

meg is a governed procedural-memory layer for AI coding agents, backed by
FalkorDB. It records successful task procedures as shared graph paths so later
agents can recall the steps that worked.

## M1: run the core store

```bash
cp .env.example .env
docker compose up -d falkordb
python -m pip install -e '.[dev]'
pytest
```

Each tenant is an isolated FalkorDB graph named `tenant:<tenant_id>`. M1 creates
the core models, safe tenant selection, and idempotent range/vector indexes.
