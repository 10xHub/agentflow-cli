# Store Module Integration Tests

This directory contains integration tests for the pyagenity-api store module API endpoints.

## Test Coverage

### API Endpoint Tests (`test_store_api.py`)

#### 1. Create Memory Endpoint (`POST /v1/store/memories`)
- ✅ Successfully create memory with string content
- ✅ Create memory with Message content
- ✅ Validation error on missing content
- ✅ Memory type validation
- ✅ Metadata handling

#### 2. Search Memories Endpoint (`POST /v1/store/search`)
- ✅ Successfully search memories
- ✅ Search with filters
- ✅ Search with retrieval strategy
- ✅ Validation error on missing query
- ✅ Invalid limit handling
- ✅ Empty results handling

#### 3. Get Memory Endpoint (`GET /v1/store/memories/{memory_id}`)
- ✅ Successfully retrieve memory
- ✅ Invalid UUID format
- ✅ Non-existent memory (404)
- ✅ With custom config
- ✅ With options
- ✅ Response structure validation

#### 4. List Memories Endpoint (`GET /v1/store/memories`)
- ✅ Successfully list memories
- ✅ With custom limit
- ✅ Invalid limit handling
- ✅ Empty results
- ✅ With options
- ✅ Pagination metadata

#### 5. Update Memory Endpoint (`PUT /v1/store/memories/{memory_id}`)
- ✅ Successfully update memory
- ✅ Update with string content
- ✅ Update with Message content
- ✅ Validation error on missing content
- ✅ Invalid UUID handling

#### 6. Delete Memory Endpoint (`DELETE /v1/store/memories/{memory_id}`)
- ✅ Successfully delete memory
- ✅ Invalid UUID format
- ✅ Non-existent memory
- ✅ Response confirmation

#### 7. Forget Memory Endpoint (`POST /v1/store/memories/forget`)
- ✅ Forget by memory type
- ✅ Forget by category
- ✅ Forget with filters
- ✅ With options
- ✅ Empty request handling
- ✅ Response count

#### 8. Authentication Tests
- ✅ All endpoints require authentication
- ✅ Missing token returns 401
- ✅ Invalid token handling
- ✅ Token verification

**Total Integration Tests: 45 tests**

---

## Current Status

⚠️ **Integration tests are written but require InjectQ container setup to run**

The tests encounter the following error:
```
injectq.utils.exceptions.InjectionError: No InjectQ container in current request context. 
Did you call setup_fastapi(app, container)?
```

### Required Setup

To make these tests functional, the `conftest.py` app fixture needs to:

1. Create an InjectQ container
2. Register StoreService with the container
3. Call `setup_fastapi(app, container)` before returning the app

Example fix needed in `conftest.py`:
```python
from injectq import Container

@pytest.fixture
def app(mock_store, mock_auth_user):
    """Create test app with mocked dependencies and InjectQ setup."""
    from pyagenity_api.src.app.main import app
    
    # Create and configure InjectQ container
    container = Container()
    mock_service = StoreService(store=mock_store)
    container.register(StoreService, instance=mock_service)
    
    # Setup FastAPI with InjectQ
    from injectq import setup_fastapi
    setup_fastapi(app, container)
    
    # Override authentication
    with patch("pyagenity_api.src.app.routers.store.router.verify_current_user", 
               return_value=mock_auth_user):
        yield app
```

---

## Running the Tests

### Once InjectQ setup is complete:

```bash
# Run all integration tests
pytest tests/integration_tests/store/ -v

# Run with coverage
pytest tests/integration_tests/store/ --cov=pyagenity_api/src/app/routers/store --cov-report=term-missing

# Run specific test file
pytest tests/integration_tests/store/test_store_api.py -v

# Run specific test class
pytest tests/integration_tests/store/test_store_api.py::TestCreateMemoryEndpoint -v

# Run specific test method
pytest tests/integration_tests/store/test_store_api.py::TestCreateMemoryEndpoint::test_create_memory_success -v
```

---

## Test Structure

### Fixtures (`conftest.py`)

- `mock_store`: AsyncMock of BaseStore
- `mock_auth_user`: Mock authenticated user
- `app`: FastAPI test application (needs InjectQ setup)
- `client`: TestClient for making HTTP requests
- `auth_headers`: Authorization headers with bearer token

### Test Organization

All tests follow this pattern:
1. **Arrange**: Setup test data and mocks
2. **Act**: Make HTTP request via TestClient
3. **Assert**: Verify response status, body, and headers

---

## API Endpoints Tested

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/store/memories` | Create new memory |
| POST | `/v1/store/search` | Search memories |
| GET | `/v1/store/memories/{memory_id}` | Get memory by ID |
| GET | `/v1/store/memories` | List all memories |
| PUT | `/v1/store/memories/{memory_id}` | Update memory |
| DELETE | `/v1/store/memories/{memory_id}` | Delete memory |
| POST | `/v1/store/memories/forget` | Forget memories by criteria |

---

## Test Scenarios Covered

### Happy Path
- Valid requests with all required fields
- Successful CRUD operations
- Proper authentication

### Edge Cases
- Invalid UUIDs
- Missing required fields
- Invalid data types
- Empty results
- Non-existent resources

### Error Handling
- 400 Bad Request (validation errors)
- 401 Unauthorized (missing/invalid auth)
- 404 Not Found (non-existent resources)
- 422 Unprocessable Entity (schema validation)

### Authentication
- All endpoints require valid JWT bearer token
- Missing token returns 401
- Invalid token handling

---

## Next Steps

1. **Fix InjectQ Setup**: Update `conftest.py` to properly initialize InjectQ container
2. **Run Tests**: Execute integration tests and verify all pass
3. **Add More Tests**: Consider adding tests for:
   - Rate limiting
   - Concurrent requests
   - Large payload handling
   - Timeout scenarios
   - Database connection errors

---

## Reference

For InjectQ setup examples, see:
- `tests/integration_tests/test_graph_api.py`
- `tests/integration_tests/test_checkpointer_api.py`
- InjectQ documentation: https://github.com/your-org/injectq

---

## Notes

- Integration tests validate the full request/response cycle
- Uses FastAPI's TestClient for synchronous testing of async endpoints
- Mocks are used to isolate API layer from actual database operations
- All tests include authentication headers
- Response validation checks status codes, JSON structure, and data types
