from meg.gate.rollback import CanaryState,evaluate_canary
def test_canary_regression_rolls_back():
 assert evaluate_canary(CanaryState(1,2),1,.8)[1]=="rolled_back"
