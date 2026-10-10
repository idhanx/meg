from meg.agent.config_store import AgentConfig
from meg.agent.simulator import simulate
def test_config_version_changes_tool_routing_behavior():
    base=AgentConfig(version=1,workflow=["plan","verify"])
    routed=AgentConfig(version=2,workflow=["plan","verify"],tool_routes=[{"pattern":"find usage","prefer":["grep","read"]}])
    assert simulate("find usage of config",routed)["steps"]<simulate("find usage of config",base)["steps"]
