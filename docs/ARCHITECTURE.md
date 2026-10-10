# Architecture

`Agent → REST/MCP → MegService → tenant:<id> FalkorDB graph → UI`.

Each tenant uses a separate FalkorDB graph. Procedures connect shared `Step` nodes,
files, verification commands, policies, and immutable access-audit edges.
