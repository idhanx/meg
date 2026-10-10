from meg.gate.gates import gate
from meg.gate.proposals import Proposal

def test_safety_loosening_never_auto_promotes():
    proposal=Proposal("safety_rules",{"path":"/safety_rules/-","value":{"effect":"allow"}},{"one","two","three"},1.0,[1.0,1.0])
    status,_,reason=gate(proposal)
    assert status=="gated"
    assert "human approval" in reason
