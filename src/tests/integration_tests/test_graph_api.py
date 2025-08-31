from collections.abc import AsyncIterator
from typing import Any

from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient
from fastapi_injector import attach_injector
from injector import Injector, Module, provider, singleton

from src.app.core.config.setup_middleware import setup_middleware
from src.app.routers.graph.router import router as graph_router
from src.app.routers.graph.schemas.graph_schemas import (
    GraphInfoSchema,
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphStreamChunkSchema,
)
from src.app.routers.graph.services.graph_service import GraphService


HTTP_OK = 200
HTTP_UNPROCESSABLE = 422


class FakeGraphService(GraphService):
    def __init__(self):  # type: ignore[no-untyped-def]
        # Bypass parent __init__ expecting graph/generator/thread_service
        pass

    async def invoke_graph(  # type: ignore[override]
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> GraphInvokeOutputSchema:
        # Build a minimal message-like payload compatible with the schema
        msg = {"role": "user", "content": "ok", "message_id": "1"}
        return GraphInvokeOutputSchema(
            messages=[msg],  # type: ignore[arg-type]
            state={"k": 1},
            context=None,
            summary=None,
            meta={},
        )

    async def stream_graph(  # type: ignore[override]
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> AsyncIterator[GraphStreamChunkSchema]:
        yield GraphStreamChunkSchema(data={"n": 1}, metadata={})
        yield GraphStreamChunkSchema(data={"n": 2}, metadata={})

    async def graph_details(self) -> GraphSchema:  # type: ignore[override]
        info = GraphInfoSchema(
            node_count=1,
            edge_count=0,
            checkpointer=False,
            checkpointer_type=None,
            publisher=False,
            store=False,
            interrupt_before=None,
            interrupt_after=None,
        )
        return GraphSchema(info=info, nodes=[{"id": "n1", "name": "N1"}], edges=[])  # type: ignore[arg-type]

    async def get_state_schema(self) -> dict:  # type: ignore[override]
        return {"title": "State", "type": "object"}


class TestModule(Module):
    @singleton
    @provider
    def provide_graph_service(self) -> GraphService:
        return FakeGraphService()


def _make_app() -> TestClient:
    app = FastAPI()
    setup_middleware(app)
    injector = Injector([TestModule()])
    attach_injector(app, injector=injector)
    app.include_router(graph_router)
    return TestClient(app)


def test_graph_invoke_success():
    c = _make_app()
    payload = {
        "messages": [{"role": "user", "content": "hi"}],
    }
    r = c.post("/v1/graph/invoke", json=payload)
    assert r.status_code == HTTP_OK
    body = r.json()["data"]
    assert "messages" in body and body["state"] == {"k": 1}


def test_graph_invoke_422_for_missing_messages():
    c = _make_app()
    r = c.post("/v1/graph/invoke", json={})
    assert r.status_code == HTTP_UNPROCESSABLE


def test_graph_details_success():
    c = _make_app()
    r = c.get("/v1/graph")
    assert r.status_code == HTTP_OK
    body = r.json()["data"]
    assert body["info"]["node_count"] == 1


def test_state_schema_success():
    c = _make_app()
    r = c.get("/v1/graph:StateSchema")
    assert r.status_code == HTTP_OK
    assert r.json()["data"]["title"] == "State"


def test_graph_stream_success():
    c = _make_app()
    payload = {
        "messages": [{"role": "user", "content": "hi"}],
    }
    # TestClient exposes the underlying httpx client; stream via c.stream(...)
    with c.stream("POST", "/v1/graph/stream", json=payload) as r:
        assert r.status_code == HTTP_OK
        chunks = list(r.iter_text())
    # Make sure at least two data lines present
    assert any("data:" in ch for ch in chunks)
