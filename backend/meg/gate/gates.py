from meg.gate.proposals import Proposal,validate
def gate(proposal:Proposal)->tuple[str,float,str]:
 ok,reason=validate(proposal)
 if not ok:return "rejected",0.,reason
 calibration=sum(proposal.reviewer_calibrations)/max(1,len(proposal.reviewer_calibrations))
 confidence=min(1.,proposal.confidence*calibration*min(1.,len(proposal.supporting_traces)/3))
 if proposal.surface=="safety_rules" and proposal.change.get("value",{}).get("effect")!="deny":return "gated",confidence,"safety loosening needs human approval"
 return ("candidate" if confidence>=.8 else "gated"),confidence,"confidence gate"
