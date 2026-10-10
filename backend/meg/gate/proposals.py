from dataclasses import dataclass
from meg.agent.config_store import ALLOWED_SURFACES
@dataclass(frozen=True)
class Proposal: surface:str; change:dict; supporting_traces:set[str]; confidence:float; reviewer_calibrations:list[float]
def validate(proposal:Proposal)->tuple[bool,str]:
 if proposal.surface not in ALLOWED_SURFACES:return False,"out-of-scope surface"
 if not proposal.change.get("path","").startswith("/"+proposal.surface):return False,"patch escapes surface"
 if len(proposal.supporting_traces)<3:return False,"insufficient distinct trace support"
 return True,"valid"
