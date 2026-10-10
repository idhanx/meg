from dataclasses import dataclass
from typing import Protocol
@dataclass(frozen=True)
class Finding: dimension:str; severity:str; description:str; evidence_event_ids:list[str]
@dataclass(frozen=True)
class Review: reviewer_id:str; scores:dict[str,int]; findings:list[Finding]; overall:float; verdict:str
class TraceReader(Protocol):
    def get_trace(self,trace_id:str)->dict: ...
def valid_findings(findings:list[Finding],event_ids:set[str])->list[Finding]:
    return [finding for finding in findings if finding.evidence_event_ids and set(finding.evidence_event_ids)<=event_ids]
