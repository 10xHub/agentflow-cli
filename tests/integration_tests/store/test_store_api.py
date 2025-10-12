"""Integration tests for store API endpoints."""

import json
from uuid import uuid4

import pytest
from pyagenity.store.store_schema import MemoryType


class TestCreateMemoryEndpoint:
    """Tests for POST /v1/store/memories endpoint."""

    def test_create_memory_success(self, client, mock_store, auth_headers):
        """Test successful memory creation."""
        # Arrange
        memory_id = str(uuid4())
        mock_store.astore.return_value = memory_id
        payload = {
            "content": "Test memory content",
            "memory_type": "episodic",
            "category": "general",
            "metadata": {"key": "value"},
        }

        # Act
        response = client.post(
            "/v1/store/memories", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Memory stored successfully"
        assert data["data"]["memory_id"] == memory_id

    def test_create_memory_with_minimal_fields(
        self, client, mock_store, auth_headers
    ):
        """Test memory creation with only required fields."""
        # Arrange
        memory_id = str(uuid4())
        mock_store.astore.return_value = memory_id
        payload = {"content": "Minimal memory"}

        # Act
        response = client.post(
            "/v1/store/memories", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["memory_id"] == memory_id

    def test_create_memory_with_config_and_options(
        self, client, mock_store, auth_headers
    ):
        """Test memory creation with config and options."""
        # Arrange
        memory_id = str(uuid4())
        mock_store.astore.return_value = memory_id
        payload = {
            "content": "Test memory",
            "config": {"model": "custom"},
            "options": {"timeout": 30},
        }

        # Act
        response = client.post(
            "/v1/store/memories", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["memory_id"] == memory_id

    def test_create_memory_missing_content(self, client, auth_headers):
        """Test memory creation without required content field."""
        # Arrange
        payload = {"category": "general"}

        # Act
        response = client.post(
            "/v1/store/memories", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_create_memory_invalid_memory_type(self, client, auth_headers):
        """Test memory creation with invalid memory type."""
        # Arrange
        payload = {"content": "Test", "memory_type": "invalid_type"}

        # Act
        response = client.post(
            "/v1/store/memories", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestSearchMemoriesEndpoint:
    """Tests for POST /v1/store/search endpoint."""

    def test_search_memories_success(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test successful memory search."""
        # Arrange
        mock_store.asearch.return_value = sample_memory_results
        payload = {"query": "test query"}

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["results"]) == 2
        assert data["data"]["results"][0]["content"] == "First memory"

    def test_search_memories_with_filters(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test memory search with filters."""
        # Arrange
        mock_store.asearch.return_value = sample_memory_results
        payload = {
            "query": "test query",
            "memory_type": "episodic",
            "category": "general",
            "limit": 5,
            "score_threshold": 0.8,
            "filters": {"tag": "important"},
        }

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["results"]) == 2

    def test_search_memories_with_retrieval_strategy(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test memory search with retrieval strategy."""
        # Arrange
        mock_store.asearch.return_value = sample_memory_results
        payload = {
            "query": "test query",
            "retrieval_strategy": "hybrid",
            "distance_metric": "euclidean",
            "max_tokens": 2000,
        }

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_search_memories_empty_results(
        self, client, mock_store, auth_headers
    ):
        """Test memory search with no results."""
        # Arrange
        mock_store.asearch.return_value = []
        payload = {"query": "nonexistent query"}

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["results"]) == 0

    def test_search_memories_missing_query(self, client, auth_headers):
        """Test memory search without required query."""
        # Arrange
        payload = {"limit": 10}

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_search_memories_invalid_limit(self, client, auth_headers):
        """Test memory search with invalid limit."""
        # Arrange
        payload = {"query": "test", "limit": 0}

        # Act
        response = client.post(
            "/v1/store/search", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestGetMemoryEndpoint:
    """Tests for GET /v1/store/memories/{memory_id} endpoint."""

    def test_get_memory_success(
        self, client, mock_store, auth_headers, sample_memory_id, sample_memory_result
    ):
        """Test successful memory retrieval."""
        # Arrange
        mock_store.aget.return_value = sample_memory_result

        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["memory"]["id"] == sample_memory_id
        assert data["data"]["memory"]["content"] == "This is a test memory"

    def test_get_memory_with_config(
        self, client, mock_store, auth_headers, sample_memory_id, sample_memory_result
    ):
        """Test memory retrieval with config parameter."""
        # Arrange
        mock_store.aget.return_value = sample_memory_result
        config = json.dumps({"include_metadata": True})

        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}",
            params={"config": config},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_memory_with_options(
        self, client, mock_store, auth_headers, sample_memory_id, sample_memory_result
    ):
        """Test memory retrieval with options parameter."""
        # Arrange
        mock_store.aget.return_value = sample_memory_result
        options = json.dumps({"include_deleted": False})

        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}",
            params={"options": options},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_memory_not_found(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test retrieving non-existent memory."""
        # Arrange
        mock_store.aget.return_value = None

        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["memory"] is None

    def test_get_memory_invalid_json_config(
        self, client, auth_headers, sample_memory_id
    ):
        """Test memory retrieval with invalid JSON config."""
        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}",
            params={"config": "invalid json"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400

    def test_get_memory_non_dict_config(
        self, client, auth_headers, sample_memory_id
    ):
        """Test memory retrieval with non-dict config."""
        # Act
        response = client.get(
            f"/v1/store/memories/{sample_memory_id}",
            params={"config": json.dumps(["list", "not", "dict"])},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400


class TestListMemoriesEndpoint:
    """Tests for GET /v1/store/memories endpoint."""

    def test_list_memories_success(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test successful memory listing."""
        # Arrange
        mock_store.aget_all.return_value = sample_memory_results

        # Act
        response = client.get("/v1/store/memories", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["memories"]) == 2
        assert data["data"]["memories"][0]["content"] == "First memory"

    def test_list_memories_with_custom_limit(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test memory listing with custom limit."""
        # Arrange
        mock_store.aget_all.return_value = sample_memory_results[:1]

        # Act
        response = client.get(
            "/v1/store/memories", params={"limit": 1}, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["memories"]) == 1

    def test_list_memories_with_config(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test memory listing with config parameter."""
        # Arrange
        mock_store.aget_all.return_value = sample_memory_results
        config = json.dumps({"sort_order": "desc"})

        # Act
        response = client.get(
            "/v1/store/memories", params={"config": config}, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_memories_with_options(
        self, client, mock_store, auth_headers, sample_memory_results
    ):
        """Test memory listing with options parameter."""
        # Arrange
        mock_store.aget_all.return_value = sample_memory_results
        options = json.dumps({"sort_by": "created_at"})

        # Act
        response = client.get(
            "/v1/store/memories", params={"options": options}, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_memories_empty(self, client, mock_store, auth_headers):
        """Test memory listing when no memories exist."""
        # Arrange
        mock_store.aget_all.return_value = []

        # Act
        response = client.get("/v1/store/memories", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["memories"]) == 0

    def test_list_memories_invalid_limit(self, client, auth_headers):
        """Test memory listing with invalid limit."""
        # Act
        response = client.get(
            "/v1/store/memories", params={"limit": 0}, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestUpdateMemoryEndpoint:
    """Tests for PUT /v1/store/memories/{memory_id} endpoint."""

    def test_update_memory_success(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test successful memory update."""
        # Arrange
        mock_store.aupdate.return_value = {"updated": True}
        payload = {
            "content": "Updated content",
            "metadata": {"updated": True},
        }

        # Act
        response = client.put(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Memory updated successfully"
        assert data["data"]["success"] is True

    def test_update_memory_with_config(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory update with config."""
        # Arrange
        mock_store.aupdate.return_value = {"updated": True}
        payload = {
            "content": "Updated content",
            "config": {"version": 2},
        }

        # Act
        response = client.put(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_memory_with_options(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory update with options."""
        # Arrange
        mock_store.aupdate.return_value = {"updated": True}
        payload = {
            "content": "Updated content",
            "options": {"force": True},
        }

        # Act
        response = client.put(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_memory_missing_content(
        self, client, auth_headers, sample_memory_id
    ):
        """Test memory update without required content."""
        # Arrange
        payload = {"metadata": {"updated": True}}

        # Act
        response = client.put(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error

    def test_update_memory_with_metadata_only(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory update with content and metadata."""
        # Arrange
        mock_store.aupdate.return_value = {"updated": True}
        payload = {
            "content": "Same content",
            "metadata": {"new_key": "new_value"},
        }

        # Act
        response = client.put(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteMemoryEndpoint:
    """Tests for DELETE /v1/store/memories/{memory_id} endpoint."""

    def test_delete_memory_success(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test successful memory deletion."""
        # Arrange
        mock_store.adelete.return_value = {"deleted": True}

        # Act
        response = client.delete(
            f"/v1/store/memories/{sample_memory_id}", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Memory deleted successfully"
        assert data["data"]["success"] is True

    def test_delete_memory_with_config(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory deletion with config."""
        # Arrange
        mock_store.adelete.return_value = {"deleted": True}
        payload = {"config": {"soft_delete": True}}

        # Act
        response = client.delete(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_memory_with_options(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory deletion with options."""
        # Arrange
        mock_store.adelete.return_value = {"deleted": True}
        payload = {"options": {"force": True}}

        # Act
        response = client.delete(
            f"/v1/store/memories/{sample_memory_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_memory_without_payload(
        self, client, mock_store, auth_headers, sample_memory_id
    ):
        """Test memory deletion without payload."""
        # Arrange
        mock_store.adelete.return_value = {"deleted": True}

        # Act
        response = client.delete(
            f"/v1/store/memories/{sample_memory_id}", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestForgetMemoryEndpoint:
    """Tests for POST /v1/store/memories/forget endpoint."""

    def test_forget_memory_with_memory_type(
        self, client, mock_store, auth_headers
    ):
        """Test forgetting memories by type."""
        # Arrange
        mock_store.aforget_memory.return_value = {"count": 5}
        payload = {"memory_type": "episodic"}

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Memories removed successfully"
        assert data["data"]["success"] is True

    def test_forget_memory_with_category(
        self, client, mock_store, auth_headers
    ):
        """Test forgetting memories by category."""
        # Arrange
        mock_store.aforget_memory.return_value = {"count": 3}
        payload = {"category": "work"}

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forget_memory_with_filters(
        self, client, mock_store, auth_headers
    ):
        """Test forgetting memories with filters."""
        # Arrange
        mock_store.aforget_memory.return_value = {"count": 2}
        payload = {
            "memory_type": "semantic",
            "category": "personal",
            "filters": {"tag": "old"},
        }

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forget_memory_with_config_and_options(
        self, client, mock_store, auth_headers
    ):
        """Test forgetting memories with config and options."""
        # Arrange
        mock_store.aforget_memory.return_value = {"count": 1}
        payload = {
            "memory_type": "episodic",
            "config": {"dry_run": True},
            "options": {"verbose": True},
        }

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forget_memory_empty_payload(
        self, client, mock_store, auth_headers
    ):
        """Test forgetting memories with empty payload."""
        # Arrange
        mock_store.aforget_memory.return_value = {"count": 0}
        payload = {}

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forget_memory_invalid_memory_type(self, client, auth_headers):
        """Test forgetting memories with invalid memory type."""
        # Arrange
        payload = {"memory_type": "invalid_type"}

        # Act
        response = client.post(
            "/v1/store/memories/forget", json=payload, headers=auth_headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestAuthenticationRequirement:
    """Tests to verify authentication is required for all endpoints."""

    def test_create_memory_without_auth(self, client):
        """Test that create memory requires authentication."""
        payload = {"content": "Test"}
        response = client.post("/v1/store/memories", json=payload)
        # The exact status code depends on auth implementation
        # but it should not be 200
        assert response.status_code != 200

    def test_search_memories_without_auth(self, client):
        """Test that search memories requires authentication."""
        payload = {"query": "test"}
        response = client.post("/v1/store/search", json=payload)
        assert response.status_code != 200

    def test_get_memory_without_auth(self, client):
        """Test that get memory requires authentication."""
        response = client.get("/v1/store/memories/test-id")
        assert response.status_code != 200

    def test_list_memories_without_auth(self, client):
        """Test that list memories requires authentication."""
        response = client.get("/v1/store/memories")
        assert response.status_code != 200

    def test_update_memory_without_auth(self, client):
        """Test that update memory requires authentication."""
        payload = {"content": "Updated"}
        response = client.put("/v1/store/memories/test-id", json=payload)
        assert response.status_code != 200

    def test_delete_memory_without_auth(self, client):
        """Test that delete memory requires authentication."""
        response = client.delete("/v1/store/memories/test-id")
        assert response.status_code != 200

    def test_forget_memory_without_auth(self, client):
        """Test that forget memory requires authentication."""
        payload = {}
        response = client.post("/v1/store/memories/forget", json=payload)
        assert response.status_code != 200
