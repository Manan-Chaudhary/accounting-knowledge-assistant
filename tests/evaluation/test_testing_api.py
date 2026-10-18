from __future__ import annotations

from io import StringIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import testing


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15


@pytest.fixture(autouse=True)
def reset_run_state():
    with testing._runs_lock:
        testing._runs.clear()
        testing._active_run_id = None

    yield

    with testing._runs_lock:
        testing._runs.clear()
        testing._active_run_id = None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(testing, "_require_team", lambda request: None)

    app = FastAPI()
    app.include_router(testing.router)

    return TestClient(app)


def test_config_lists_runnable_test_set_and_models(client):
    response = client.get("/api/testing/config")

    assert response.status_code == 200
    payload = response.json()

    assert payload["test_sets"][0]["id"] == "core-mvp"
    assert payload["test_sets"][0]["case_count"] > 0
    assert any(model["id"] == "gemini-3-8-flash" for model in payload["models"])
    assert payload["defaults"]["retrieval_strategy"] == "hybrid"


def test_start_rejects_unknown_model(client):
    response = client.post(
        "/api/testing/runs",
        json={
            "test_set": "core-mvp",
            "model": "not-a-real-model",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown evaluation model."


def test_run_can_start_and_status_can_be_read(client, monkeypatch):
    fake_process = FakeProcess()

    monkeypatch.setattr(
        testing,
        "_spawn_process",
        lambda **kwargs: (fake_process, StringIO()),
    )
    monkeypatch.setattr(
        testing,
        "_launch_monitor",
        lambda *args, **kwargs: None,
    )

    started = client.post(
        "/api/testing/runs",
        json={
            "test_set": "core-mvp",
            "model": "gemini-3-8-flash",
            "retrieval_strategy": "hybrid",
        },
    )

    assert started.status_code == 202
    run = started.json()
    assert run["status"] == "running"
    assert run["total"] > 0

    status_response = client.get(f"/api/testing/runs/{run['run_id']}")

    assert status_response.status_code == 200
    assert status_response.json()["run_id"] == run["run_id"]
    assert status_response.json()["status"] == "running"


def test_active_run_can_be_recovered(client, monkeypatch):
    fake_process = FakeProcess()

    monkeypatch.setattr(
        testing,
        "_spawn_process",
        lambda **kwargs: (fake_process, StringIO()),
    )
    monkeypatch.setattr(
        testing,
        "_launch_monitor",
        lambda *args, **kwargs: None,
    )

    started = client.post(
        "/api/testing/runs",
        json={
            "test_set": "core-mvp",
            "model": "gemini-3-8-flash",
        },
    ).json()

    response = client.get("/api/testing/runs/active")

    assert response.status_code == 200
    assert response.json()["run_id"] == started["run_id"]


def test_stop_marks_run_stopping_and_terminates_process(client, monkeypatch):
    fake_process = FakeProcess()

    monkeypatch.setattr(
        testing,
        "_spawn_process",
        lambda **kwargs: (fake_process, StringIO()),
    )
    monkeypatch.setattr(
        testing,
        "_launch_monitor",
        lambda *args, **kwargs: None,
    )

    started = client.post(
        "/api/testing/runs",
        json={
            "test_set": "core-mvp",
            "model": "gemini-3-8-flash",
        },
    ).json()

    response = client.post(
        f"/api/testing/runs/{started['run_id']}/stop"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "stopping"
    assert fake_process.terminated is True


def test_summary_applies_supported_gates(monkeypatch):
    fake_summary = {
        "cases": 2,
        "provider_failures": 0,
        "answer_returned": 1.0,
        "source_hit": 1.0,
        "top1_hit": 1.0,
        "recall_at_k": 1.0,
        "mrr": 0.75,
        "citation_present": 1.0,
        "citation_valid": 1.0,
        "citation_format_standard": 1.0,
        "refusal_correct": 1.0,
        "refusal_recall": 1.0,
        "refusal_precision": 1.0,
        "judge_correctness": 4.5,
        "judge_faithfulness": 4.75,
        "p50_latency_ms": 2000,
        "p95_latency_ms": 9000,
    }

    monkeypatch.setattr(testing, "summarise", lambda results: fake_summary)
    monkeypatch.setattr(testing, "case_failures", lambda result: [])

    summary = testing._build_summary([{"id": "A"}, {"id": "B"}])
    cards = {card["key"]: card for card in summary["metric_cards"]}

    assert cards["recall_at_k"]["outcome"] == "pass"
    assert cards["citation_valid"]["outcome"] == "pass"
    assert cards["p95_latency_ms"]["outcome"] == "fail"
    assert cards["judge_correctness"]["outcome"] == "info"
    assert summary["gates_met"] is False
