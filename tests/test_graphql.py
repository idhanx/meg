from fastapi.testclient import TestClient
from meg.api import create_app
class Service:
 def active_config(self,tenant_id):return {"version":1,"body":{},"hash":"x"}
def test_graphql_active_config_uses_shared_service():
    client=TestClient(create_app(Service()))
    response=client.post("/graphql",json={"query":"{ activeConfig(tenantId: \"demo\") }"})
    assert response.json()["data"]["activeConfig"]["version"]==1
