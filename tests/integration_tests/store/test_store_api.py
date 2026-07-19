"""Live store API tests.

Uses the store fixtures in ``conftest.py`` (real router + service over a mocked
``BaseStore``). The mock stands in for a vector DB, but the assertions verify the real
router/service behaviour -- including that the authenticated ``user_id`` is forwarded to
the backend config, which is what a real store would scope on.
"""

from __future__ import annotations

from uuid import uuid4


HTTP_OK = 200


def test_create_memory_success(client, mock_store, auth_headers):
    memory_id = str(uuid4())
    mock_store.astore.return_value = memory_id

    payload = {
        "content": "Test memory content",
        "memory_type": "episodic",
        "category": "general",
        "metadata": {"key": "value"},
    }
    resp = client.post("/v1/store/memories", json=payload, headers=auth_headers)

    assert resp.status_code == HTTP_OK
    body = resp.json()
    assert body["data"]["memory_id"] == memory_id


def test_create_memory_forwards_user_scope_to_backend(client, mock_store, auth_headers):
    """The store must receive a ``user_id`` in its config -- the scoping signal a real
    backend keys on. (This fixture runs auth-disabled, so the value is 'anonymous'; the
    authenticated-value path is covered by the IDOR tests that wire real auth.)"""
    mock_store.astore.return_value = str(uuid4())

    client.post(
        "/v1/store/memories",
        json={"content": "hi", "memory_type": "episodic"},
        headers=auth_headers,
    )

    assert mock_store.astore.await_count == 1
    cfg = mock_store.astore.await_args.args[0]
    assert "user_id" in cfg


def test_search_memories_success(client, mock_store, auth_headers, sample_memory_results):
    mock_store.asearch.return_value = sample_memory_results

    resp = client.post(
        "/v1/store/search",
        json={"query": "test", "limit": 5},
        headers=auth_headers,
    )

    assert resp.status_code == HTTP_OK
