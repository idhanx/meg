from meg.gate.proposals import Proposal
from meg.gate.gates import gate
def p(**x):return Proposal("tool_routes",{"path":"/tool_routes/-"},{"a","b","c"},.9,[.9,.9],**x)
def test_low_confidence_gated_and_scope_rejected():
 assert gate(Proposal("bad",{"path":"/bad"},{"a","b","c"},1,[1]))[0]=="rejected"
 assert gate(Proposal("tool_routes",{"path":"/tool_routes/-"},{"a","b","c"},.2,[.9]))[0]=="gated"
