# from typing import Any

# from fastapi import FastAPI
# from fastapi.testclient import TestClient
# from fastapi_injector import attach_injector
# from injector import Injector, Module, provider, singleton
# from pyagenity.utils import Message

# from src.app.core.config.setup_middleware import setup_middleware
# from src.app.routers.checkpointer.router import router as checkpointer_router
# from src.app.routers.checkpointer.schemas.checkpointer_schemas import (
#     MessagesListResponseSchema,
#     ResponseSchema,
#     StateResponseSchema,
#     ThreadResponseSchema,
#     ThreadsListResponseSchema,
# )
# from src.app.routers.checkpointer.services.checkpointer_service import CheckpointerService


# HTTP_OK = 200
# HTTP_UNPROCESSABLE = 422


# class FakeCheckpointerService(CheckpointerService):
#     def __init__(self):  # type: ignore[no-untyped-def]
#         pass

#     async def get_state(self, config: dict[str, Any], user: dict) -> StateResponseSchema:  # type: ignore[override]
#         return StateResponseSchema(state={"a": 1})

#     async def put_state(  # type: ignore[override]
#         self, config: dict[str, Any], user: dict, state: dict[str, Any]
#     ) -> StateResponseSchema:
#         return StateResponseSchema(state=state)

#     async def clear_state(self, config: dict[str, Any], user: dict) -> ResponseSchema:  # type: ignore[override]
#         return ResponseSchema(success=True, message="State cleared successfully", data=None)

#     async def put_messages(  # type: ignore[override]
#         self, config: dict[str, Any], user: dict, messages: list[Message], metadata: dict | None
#     ) -> ResponseSchema:
#         return ResponseSchema(success=True, message="ok", data=len(messages))

#     async def get_message(self, config: dict[str, Any], user: dict, message_id: Any) -> Message:  # type: ignore[override]
#         return Message.from_text(role="user", data="hi", message_id="1")  # type: ignore[arg-type]

#     async def get_messages(
#         self,
#         config: dict[str, Any],
#         user: dict,
#         search: str | None = None,
#         offset: int | None = None,
#         limit: int | None = None,
#     ) -> MessagesListResponseSchema:  # type: ignore[override]
#         return MessagesListResponseSchema(
#             messages=[Message.from_text(role="user", data="hi", message_id="1")]
#         )  # type: ignore[arg-type]

#     async def delete_message(  # type: ignore[override]
#         self, config: dict[str, Any], user: dict, message_id: Any
#     ) -> ResponseSchema:
#         return ResponseSchema(success=True, message="deleted", data=str(message_id))

#     async def get_thread(self, config: dict[str, Any], user: dict) -> ThreadResponseSchema:  # type: ignore[override]
#         return ThreadResponseSchema(thread={"id": config.get("thread_id")})

#     async def list_threads(  # type: ignore[override]
#         self,
#         user: dict,
#         search: str | None = None,
#         offset: int | None = None,
#         limit: int | None = None,
#     ) -> ThreadsListResponseSchema:
#         return ThreadsListResponseSchema(threads=[{"id": 1}])

#     async def delete_thread(  # type: ignore[override]
#         self, config: dict[str, Any], user: dict, thread_id: Any
#     ) -> ResponseSchema:
#         return ResponseSchema(success=True, message="deleted", data=str(thread_id))


# class TestModule(Module):
#     @singleton
#     @provider
#     def provide_checkpointer_service(self) -> CheckpointerService:
#         return FakeCheckpointerService()


# def _client() -> TestClient:
#     app = FastAPI()
#     setup_middleware(app)
#     injector = Injector([TestModule()])
#     attach_injector(app, injector=injector)
#     app.include_router(checkpointer_router)
#     return TestClient(app)


# def test_get_state_success():
#     c = _client()
#     r = c.get("/v1/threads/1/state")
#     assert r.status_code == HTTP_OK
#     assert r.json()["data"]["state"] == {"a": 1}


# def test_put_state_success_and_422():
#     c = _client()
#     # success
#     r = c.put("/v1/threads/1/state", json={"state": {"b": 2}})
#     assert r.status_code == HTTP_OK
#     assert r.json()["data"]["state"] == {"b": 2}
#     # 422 when missing required field
#     r2 = c.put("/v1/threads/1/state", json={})
#     assert r2.status_code == HTTP_UNPROCESSABLE


# def test_clear_state_success():
#     c = _client()
#     r = c.delete("/v1/threads/1/state")
#     assert r.status_code == HTTP_OK
#     assert r.json()["data"]["message"] == "State cleared successfully"


# def test_put_messages_and_list_and_get_and_delete():
#     c = _client()
#     r = c.post(
#         "/v1/threads/1/messages",
#         json={"messages": [], "metadata": {}},
#     )
#     assert r.status_code == HTTP_OK
#     # 422 when missing required messages field
#     r_bad = c.post("/v1/threads/1/messages", json={"metadata": {}})
#     assert r_bad.status_code == HTTP_UNPROCESSABLE
#     r = c.get("/v1/threads/1/messages")
#     assert r.status_code == HTTP_OK
#     r = c.get("/v1/threads/1/messages/1")
#     assert r.status_code == HTTP_OK
#     r = c.request("DELETE", "/v1/threads/1/messages/1", json={"config": {}})
#     assert r.status_code == HTTP_OK


# def test_threads_get_list_delete():
#     c = _client()
#     r = c.get("/v1/threads/1")
#     assert r.status_code == HTTP_OK
#     r = c.get("/v1/threads")
#     assert r.status_code == HTTP_OK
#     r = c.request("DELETE", "/v1/threads/1", json={"config": {}})
#     assert r.status_code == HTTP_OK
