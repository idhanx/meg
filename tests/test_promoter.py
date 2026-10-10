from meg.agent.config_store import AgentConfig
from meg.gate.promoter import Promoter
class G:
 def __init__(self):self.calls=[]
 def query(self,q,p=None):self.calls.append((q,p))
def test_only_promoter_writes_candidate_and_decision_lineage():
 g=G();p=Promoter(g);active=AgentConfig(version=1);candidate=p.candidate(active,"p1",{"path":"/instructions/-","value":"verify"});p.promote("p1",candidate,active)
 assert candidate.version==2 and any("Decision" in q for q,_ in g.calls)
