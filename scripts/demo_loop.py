"""Offline 3-minute reviewer-loop demonstration."""
from meg.agent.config_store import AgentConfig
from meg.agent.simulator import simulate
from meg.gate.gates import gate
from meg.gate.proposals import Proposal
from meg.gate.replay import replay

v1=AgentConfig(version=1,workflow=["plan","verify"])
v2=AgentConfig(version=2,workflow=["plan","verify"],tool_routes=[{"pattern":"find usage","prefer":["grep","read"]}])
tasks=[{"task":"find usage of config","pinned":True},{"task":"fix CI and verify","pinned":True}]
proposal=Proposal("tool_routes",{"path":"/tool_routes/-","value":{"pattern":"find usage","prefer":["grep","read"]}},{"t1","t2","t3"},.95,[.95,.95])
print("v1:",simulate(tasks[0]["task"],v1));print("proposal:",gate(proposal));print("replay:",replay(v1,v2,tasks))
bad=AgentConfig(version=3,workflow=["plan"]);print("bad proposal blocked:",replay(v1,bad,tasks))
