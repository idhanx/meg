"""Deterministic active-vs-candidate replay; any golden regression rejects promotion."""
from meg.agent.config_store import AgentConfig
from meg.agent.simulator import simulate
def replay(active:AgentConfig,candidate:AgentConfig,tasks:list[dict])->dict:
    active_runs=[simulate(t["task"],active) for t in tasks];candidate_runs=[simulate(t["task"],candidate) for t in tasks]
    golden_regression=any(t.get("pinned") and a["success"] and not c["success"] for t,a,c in zip(tasks,active_runs,candidate_runs))
    active_score=sum(float(x["score"]) for x in active_runs)/max(1,len(tasks));candidate_score=sum(float(x["score"]) for x in candidate_runs)/max(1,len(tasks))
    active_success=sum(bool(x["success"]) for x in active_runs);candidate_success=sum(bool(x["success"]) for x in candidate_runs)
    passed=not golden_regression and candidate_success>=active_success and (candidate_score>=active_score+.05 or sum(x["steps"] for x in candidate_runs)<sum(x["steps"] for x in active_runs))
    return {"passed":passed,"golden_regression":golden_regression,"active_score":active_score,"candidate_score":candidate_score,"active_success":active_success,"candidate_success":candidate_success}
