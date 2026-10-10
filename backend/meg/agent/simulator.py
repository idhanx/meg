"""Offline deterministic replay simulator used by gate regression tests."""
from meg.agent.config_store import AgentConfig
def simulate(task:str,config:AgentConfig)->dict[str,float|bool]:
    find_usage="find usage" in task.lower()
    routed=any(route.get("pattern") in task.lower() and "grep" in route.get("prefer",[]) for route in config.tool_routes)
    verify="verify" in config.workflow
    steps=2+(0 if not find_usage or routed else 3)+(0 if verify else 2)
    return {"success":verify,"steps":steps,"score":max(0.,1-(steps-2)*.1)}
