from fastapi.testclient import TestClient

from meg.api import create_app


class Service:
    def recall(self, tenant_id, agent_id, task, k):
        return [{"procedure_id": "p1", "why": "match", "path": ["p1"]}]

    def record(self, payload):
        from meg.ingest.merge import RecordResult
        return RecordResult("p1", None, 2, 0)

    def explain(self, tenant_id, procedure_id):
        return {"procedure_id": procedure_id}
    def audit_log(self, tenant_id, decision=None): return []
    def policies(self, tenant_id): return []
    def benchmark(self): return {"method":"simulated"}


def test_rest_api_delegates_to_shared_service() -> None:
    client = TestClient(create_app(Service()))
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/recall", json={"tenant_id": "demo", "agent_id": "a", "task": "ci"}).json()["procedures"][0]["procedure_id"] == "p1"
    assert client.post("/record", json={}).json()["procedure_id"] == "p1"
    assert client.get("/audit?tenant_id=demo").json() == {"entries": []}
    assert client.get("/bench/results").json()["method"] == "simulated"
