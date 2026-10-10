"""The only component allowed to write AgentConfig status or Decision lineage."""
from __future__ import annotations
import json
from datetime import UTC,datetime
from uuid import uuid4
from meg.agent.config_store import AgentConfig
from meg.db import Graph
class Promoter:
    def __init__(self,graph:Graph):self.graph=graph
    def candidate(self,active:AgentConfig,proposal_id:str,change:dict)->AgentConfig:
        body=active.body();path=change["path"].strip("/").split("/");surface=path[0]
        if change.get("op","add") in {"add","replace"}:
            if len(path)==1:body[surface]=change["value"]
            elif path[-1]=="-":body[surface]=[*(body.get(surface,[])),change["value"]]
        config=AgentConfig(version=active.version+1,**body);now=datetime.now(UTC).isoformat()
        self.graph.query("CREATE (c:AgentConfig {version:$version,hash:$hash,body:$body,status:'candidate',created_at:$now,parent_version:$parent}) WITH c MATCH (p:Proposal {id:$proposal}) MERGE (p)-[:YIELDS]->(c)",{"version":config.version,"hash":config.digest(),"body":json.dumps(config.body()),"now":now,"parent":active.version,"proposal":proposal_id})
        return config
    def promote(self,proposal_id:str,candidate:AgentConfig,active:AgentConfig)->None:
        now=datetime.now(UTC).isoformat();decision=str(uuid4())
        self.graph.query("MATCH (old:AgentConfig {version:$old}),(new:AgentConfig {version:$new}),(p:Proposal {id:$proposal}) SET old.status='retired',new.status='active',p.status='promoted' MERGE (new)-[:SUPERSEDES]->(old) CREATE (d:Decision {id:$id,who:'gatekeeper',gate:'promote',reason:'all gates passed',ts:$now}) MERGE (d)-[:FOR]->(p)",{"old":active.version,"new":candidate.version,"proposal":proposal_id,"id":decision,"now":now})
    def reject(self,proposal_id:str,reason:str)->None:
        self.graph.query("MATCH (p:Proposal {id:$proposal}) SET p.status='rejected' CREATE (d:Decision {id:$id,who:'gatekeeper',gate:'reject',reason:$reason,ts:$now}) MERGE (d)-[:FOR]->(p)",{"proposal":proposal_id,"id":str(uuid4()),"reason":reason,"now":datetime.now(UTC).isoformat()})
