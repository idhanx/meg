from dataclasses import dataclass
@dataclass
class CanaryState: active_version:int; candidate_version:int; rollbacks:int=0
def evaluate_canary(state:CanaryState,active_success:float,candidate_success:float)->tuple[CanaryState,str]:
    if candidate_success<active_success:return CanaryState(state.active_version,state.candidate_version,state.rollbacks+1),"rolled_back"
    return state,"canary_passed"
