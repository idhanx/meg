"""Sensitivity policy evaluation backed by Policy nodes in FalkorDB."""

from __future__ import annotations

from meg.db import Graph
from meg.models import Sensitivity

LEVEL = {Sensitivity.PUBLIC.value: 0, Sensitivity.INTERNAL.value: 1, Sensitivity.RESTRICTED.value: 2}
DEFAULT_POLICIES = (("developer", "read", "internal"), ("developer", "write", "internal"),
                    ("intern", "read", "internal"), ("security", "read", "restricted"),
                    ("security", "write", "restricted"), ("readonly", "read", "public"))


def allowed(role: str, action: str, sensitivity: str, policies: list[dict[str, str]]) -> tuple[bool, str]:
    matches = [p for p in policies if p["agent_role"] == role and p["action"] == action]
    if any(p["effect"] == "deny" and LEVEL[p["max_sensitivity"]] >= LEVEL[sensitivity] for p in matches):
        return False, "matching deny policy"
    if any(p["effect"] == "allow" and LEVEL[p["max_sensitivity"]] >= LEVEL[sensitivity] for p in matches):
        return True, "matching allow policy"
    return False, "no matching allow policy"


def seed_defaults(graph: Graph) -> None:
    for role, action, maximum in DEFAULT_POLICIES:
        graph.query("MERGE (p:Policy {id: $id}) SET p.name=$name, p.effect='allow', p.action=$action, p.agent_role=$role, p.max_sensitivity=$maximum",
                    {"id": f"default-{role}-{action}", "name": f"{role} may {action} through {maximum}", "role": role, "action": action, "maximum": maximum})


def policies_for(graph: Graph, procedure_id: str | None = None) -> list[dict[str, str]]:
    result = graph.query("MATCH (p:Policy) RETURN p.effect, p.action, p.agent_role, p.max_sensitivity")
    rows = list(getattr(result, "result_set", result or []))
    return [row if isinstance(row, dict) else {"effect": row[0], "action": row[1], "agent_role": row[2], "max_sensitivity": row[3]} for row in rows]
