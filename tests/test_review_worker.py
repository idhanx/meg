from meg.review.worker import ReviewWorker
class R:
 def __init__(self):self.calls=[]
 def query(self,q,p=None):self.calls.append((q,p));return type("X",(),{"result_set":[['[{"id":"e1","type":"command","exit_code":1}]']]})()
def test_worker_persists_trace_review_and_evidence_nodes():
 graph=R();w=ReviewWorker(graph);w.store_trace("t","task","failure",[],1);w.run("t")
 assert any("Trace" in q for q,_ in graph.calls) and any("Finding" in q for q,_ in graph.calls)
