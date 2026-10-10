# Implementation notes

## FalkorDB index syntax

The schema uses FalkorDB's documented `CREATE INDEX FOR (n:Label) ON (n.property)`
syntax for range indexes and `CREATE VECTOR INDEX ... OPTIONS {dimension:384,
similarityFunction:'cosine'}` for vector indexes. The server versions targeted by
this project do not provide a portable `IF NOT EXISTS` spelling for these DDL
statements, so `ensure_schema` treats an existing-index response as successful.

Vector values will be stored using `vecf32(...)`, and recall will query them via
`db.idx.vector.queryNodes` in M3.
