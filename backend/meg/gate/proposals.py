from dataclasses import dataclass
from meg.agent.config_store import ALLOWED_SURFACES
from meg.db import Graph
from uuid import uuid4
from datetime import UTC,datetime
@dataclass(frozen=True)
class Proposal: surface:str; change:dict; supporting_traces:set[str]; confidence:float; reviewer_calibrations:list[float]
def validate(proposal:Proposal)->tuple[bool,str]:
 if proposal.surface not in ALLOWED_SURFACES:return False,"out-of-scope surface"
 if not proposal.change.get("path","").startswith("/"+proposal.surface):return False,"patch escapes surface"
 if len(proposal.supporting_traces)<3:return False,"insufficient distinct trace support"
 return True,"valid"
class ProposalStore:
 def __init__(self,graph:Graph):self.graph=graph
 def submit(self,proposal:Proposal,rationale:str="")->str:
  proposal_id=str(uuid4());self.graph.query("CREATE (p:Proposal {id:$id,surface:$surface,change:$change,rationale:$rationale,confidence:$confidence,status:'submitted',created_at:$now,supporting_traces:$traces})",{"id":proposal_id,"surface":proposal.surface,"change":str(proposal.change),"rationale":rationale,"confidence":proposal.confidence,"now":datetime.now(UTC).isoformat(),"traces":list(proposal.supporting_traces)});return proposal_id
 def list(self)->list[dict]:
  rows=list(getattr(self.graph.query("MATCH (p:Proposal) RETURN p.id,p.surface,p.change,p.status,p.confidence,p.rationale ORDER BY p.created_at DESC"),"result_set",[]));return [{"id":r[0],"surface":r[1],"change":r[2],"status":r[3],"confidence":r[4],"rationale":r[5]} for r in rows]
