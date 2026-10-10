from meg.recall.rank import rank


def test_similar_task_ranks_matching_procedure_and_returns_why_and_path() -> None:
    results = rank([
        {"id": "docker", "title": "Fix Docker build", "summary": "pin node version", "task": "Docker build fails", "similarity": .8,
         "success_count": 4, "fail_count": 0, "last_used_at": "2026-10-10T00:00:00+00:00", "files": ["Dockerfile"], "path": ["docker", "step-1"]},
        {"id": "db", "title": "Run migration", "summary": "database migration", "similarity": .1, "success_count": 2, "fail_count": 0},
    ], "Fix the failing Docker build", 3)
    assert results[0]["procedure_id"] == "docker"
    assert results[0]["why"]
    assert results[0]["path"] == ["docker", "step-1"]
