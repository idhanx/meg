"""Subject agent facade; config selection is explicit at task start."""
from meg.agent.config_store import ReadOnlyConfigRepository
from meg.agent.simulator import simulate
def run_task(task:str,configs:ReadOnlyConfigRepository)->dict:
    config=configs.active();return {"config_version":config.version,"task":task,**simulate(task,config)}
