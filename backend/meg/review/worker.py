"""Graph-backed review worker. Reviewers receive only TraceReader, never this writer."""
from __future__ import annotations
import json
from datetime import UTC,datetime
from uuid import uuid4
from meg.db import Graph
from meg.review.reviewers import HeuristicReviewer

class GraphTraceReader:
    def __init__(self,graph:Graph):self.graph=graph
    def get_trace(self,trace_id:str)->dict:
        rows=list(getattr(self.graph.query("MATCH (t:Trace {id:$id}) RETURN t.events_json",{"id":trace_id}),"result_set",[]))
        return {"events":json.loads(rows[0][0])} if rows else {"events":[]}

class ReviewWorker:
    def __init__(self,graph:Graph):self.graph=graph
    def store_trace(self,trace_id:str,task:str,outcome:str,events:list[dict],config_version:int)->None:
        self.graph.query("MERGE (t:Trace {id:$id}) SET t.task=$task,t.outcome=$outcome,t.events_json=$events,t.config_version=$version,t.created_at=$now "
                         "WITH t MATCH (c:AgentConfig {version:$version}) MERGE (t)-[:RAN_WITH]->(c)",{"id":trace_id,"task":task,"outcome":outcome,"events":json.dumps(events),"version":config_version,"now":datetime.now(UTC).isoformat()})
    def run(self,trace_id:str)->list[str]:
        reader=GraphTraceReader(self.graph);ids=[]
        for reviewer in (HeuristicReviewer("process-reviewer","process"),HeuristicReviewer("outcome-reviewer","outcome_safety")):
            review=reviewer.review(reader,trace_id);review_id=str(uuid4());ids.append(review_id)
            self.graph.query("MERGE (r:Reviewer {id:$reviewer}) SET r.rubric=$rubric,r.name=$reviewer,r.model='heuristic',r.calibration_score=1.0 "
                             "CREATE (v:Review {id:$id,scores:$scores,overall:$overall,verdict:$verdict,created_at:$now}) "
                             "WITH r,v MATCH (t:Trace {id:$trace}) MERGE (r)-[:WROTE]->(v)-[:GRADES]->(t)",{"reviewer":review.reviewer_id,"rubric":reviewer.rubric,"id":review_id,"scores":json.dumps(review.scores),"overall":review.overall,"verdict":review.verdict,"now":datetime.now(UTC).isoformat(),"trace":trace_id})
            for finding in review.findings:
                self.graph.query("MATCH (v:Review {id:$review}) CREATE (f:Finding {id:$id,dimension:$dimension,severity:$severity,description:$description,evidence_event_ids:$evidence}) MERGE (v)-[:HAS_FINDING]->(f)",{"review":review_id,"id":str(uuid4()),"dimension":finding.dimension,"severity":finding.severity,"description":finding.description,"evidence":json.dumps(finding.evidence_event_ids)})
        return ids
