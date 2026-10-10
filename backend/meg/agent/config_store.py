"""Immutable, versioned AgentConfig persistence. Only the promoter writes configs."""
from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from typing import Any,Protocol
from pydantic import BaseModel,Field
from meg.db import Graph

ALLOWED_SURFACES={"instructions","recall","memory_ops","workflow","tool_routes","safety_rules"}
class AgentConfig(BaseModel):
    version:int
    instructions:list[str]=Field(default_factory=list)
    recall:dict[str,Any]=Field(default_factory=lambda:{"k":3,"weights":{"similarity":.55,"success_rate":.2,"recency":.15,"path_overlap":.1}})
    memory_ops:list[dict[str,Any]]=Field(default_factory=list)
    workflow:list[str]=Field(default_factory=lambda:["plan","recall","act","verify"])
    tool_routes:list[dict[str,Any]]=Field(default_factory=list)
    safety_rules:list[dict[str,Any]]=Field(default_factory=list)
    def body(self)->dict[str,Any]: return self.model_dump(exclude={"version"})
    def digest(self)->str:return hashlib.sha256(json.dumps(self.body(),sort_keys=True).encode()).hexdigest()

DEFAULT_CONFIG=AgentConfig(version=1,instructions=["Verify before declaring success."],tool_routes=[{"pattern":"find usage","prefer":["grep","read"]}])
class ReadOnlyConfigRepository(Protocol):
    def active(self)->AgentConfig: ...
    def get(self,version:int)->AgentConfig|None: ...

class ConfigStore:
    def __init__(self,graph:Graph):self.graph=graph
    def seed(self)->AgentConfig:
        self.graph.query("MERGE (c:AgentConfig {version:1}) ON CREATE SET c.hash=$hash,c.body=$body,c.status='active',c.created_at=$now,c.parent_version=0",{"hash":DEFAULT_CONFIG.digest(),"body":json.dumps(DEFAULT_CONFIG.body()),"now":datetime.now(UTC).isoformat()})
        return DEFAULT_CONFIG
    def active(self)->AgentConfig:
        rows=list(getattr(self.graph.query("MATCH (c:AgentConfig {status:'active'}) RETURN c.version,c.body ORDER BY c.version DESC LIMIT 1"),"result_set",[]))
        if not rows:return self.seed()
        return AgentConfig(version=rows[0][0],**json.loads(rows[0][1]))
    def get(self,version:int)->AgentConfig|None:
        rows=list(getattr(self.graph.query("MATCH (c:AgentConfig {version:$version}) RETURN c.body",{"version":version}),"result_set",[]))
        return AgentConfig(version=version,**json.loads(rows[0][0])) if rows else None
