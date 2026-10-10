from meg.agent.config_store import AgentConfig
from meg.gate.replay import replay
def test_bad_candidate_that_skips_verification_is_rejected_by_golden_replay():
 active=AgentConfig(version=1,workflow=["plan","verify"])
 bad=AgentConfig(version=2,workflow=["plan"])
 result=replay(active,bad,[{"task":"fix CI and verify","pinned":True}])
 assert not result["passed"] and result["golden_regression"]
