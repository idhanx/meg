"""GraphQL read/control surface over the same service layer used by REST."""
from __future__ import annotations
from typing import Any,Callable
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON
from meg.service import MegService

@strawberry.type
class ReviewNode:
    id:str; reviewer_id:str; trace_id:str; overall:float; verdict:str; scores:JSON
@strawberry.type
class ProposalNode:
    id:str; surface:str; status:str; confidence:float; rationale:str; change:JSON
def router(provider:Callable[[],MegService])->GraphQLRouter:
    @strawberry.type
    class Query:
        @strawberry.field
        def active_config(self,tenant_id:str)->JSON:return provider().active_config(tenant_id)
        @strawberry.field
        def reviews(self,tenant_id:str)->list[ReviewNode]:return [ReviewNode(**item) for item in provider().reviews(tenant_id)]
        @strawberry.field
        def proposals(self,tenant_id:str)->list[ProposalNode]:return [ProposalNode(**item) for item in provider().proposals(tenant_id)]
        @strawberry.field
        def lineage(self,tenant_id:str,config_version:int)->JSON:return provider().lineage(tenant_id,config_version)
        @strawberry.field
        def loop_metrics(self,tenant_id:str)->JSON:return {"versions":[]}
    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def run_review(self,tenant_id:str,trace_id:str)->list[str]:return provider().run_review(tenant_id,trace_id)
        @strawberry.mutation
        def decide_proposal(self,tenant_id:str,proposal_id:str,decision:str)->bool:
            if decision not in {"approved","reject","rolled_back"}:raise ValueError("invalid decision")
            provider().proposal_decision(tenant_id,proposal_id,decision);return True
    return GraphQLRouter(strawberry.Schema(query=Query,mutation=Mutation),graphql_ide="graphiql")
