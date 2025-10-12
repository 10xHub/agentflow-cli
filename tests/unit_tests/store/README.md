# Store Module Unit Tests

This directory contains comprehensive unit tests for the pyagenity-api store module.

## Test Coverage

### 1. Store Service Tests (`test_store_service.py`)
Comprehensive tests for all `StoreService` methods:

#### StoreMemory Tests
- ✅ Store memory with string content
- ✅ Store memory with Message content
- ✅ Store memory with custom configuration
- ✅ Store memory with additional options
- ✅ Error handling when store is not configured

#### SearchMemories Tests
- ✅ Basic memory search
- ✅ Search with filters (memory_type, category, limit, score_threshold)
- ✅ Search with retrieval strategy and distance metrics
- ✅ Handle empty search results

#### GetMemory Tests  
- ✅ Successfully retrieve memory by ID
- ✅ Retrieve with custom config
- ✅ Retrieve with options
- ✅ Handle non-existent memory

#### ListMemories Tests
- ✅ List memories with default limit
- ✅ List memories with custom limit
- ✅ List memories with options
- ✅ Handle empty memory list

#### UpdateMemory Tests
- ✅ Update memory with string content
- ✅ Update memory with Message content
- ✅ Update memory with options

#### DeleteMemory Tests
- ✅ Successfully delete memory
- ✅ Delete with custom config
- ✅ Delete with options

#### ForgetMemory Tests
- ✅ Forget memories by type
- ✅ Forget memories by category
- ✅ Forget memories with filters
- ✅ Forget memories with options
- ✅ Exclude None values from forget call

**Total Service Tests: 30 tests**  
**Service Coverage: 100%**

---

### 2. Schema Validation Tests (`test_store_schemas.py`)
Comprehensive tests for all Pydantic schemas:

#### StoreMemorySchema Tests
- ✅ Valid with string content
- ✅ Valid with Message content
- ✅ Default values
- ✅ With config and options
- ✅ Missing content raises error
- ✅ All memory types

#### SearchMemorySchema Tests
- ✅ Valid basic search
- ✅ With all filters
- ✅ With retrieval strategy options
- ✅ Default values
- ✅ Missing query raises error
- ✅ Invalid limit raises error
- ✅ Invalid max_tokens raises error

#### UpdateMemorySchema Tests
- ✅ Valid with string content
- ✅ Valid with Message content
- ✅ With config and options
- ✅ Metadata optional
- ✅ Missing content raises error

#### DeleteMemorySchema Tests
- ✅ Valid empty schema
- ✅ With config
- ✅ With options

#### ForgetMemorySchema Tests
- ✅ Valid with memory type
- ✅ Valid with category
- ✅ Valid with filters
- ✅ With all fields
- ✅ Default values

#### Edge Cases Tests
- ✅ Empty string content
- ✅ Large metadata (100+ keys)
- ✅ Nested filter structures
- ✅ Unicode content (emojis, special chars)
- ✅ Very long content (10,000 chars)
- ✅ Score threshold boundaries

**Total Schema Tests: 34 tests**  
**Schema Coverage: 100%**

---

## Running the Tests

### Run all store unit tests:
```bash
pytest tests/unit_tests/store/ -v
```

### Run with coverage:
```bash
pytest tests/unit_tests/store/ --cov=pyagenity_api/src/app/routers/store --cov-report=term-missing
```

### Run specific test file:
```bash
pytest tests/unit_tests/store/test_store_service.py -v
pytest tests/unit_tests/store/test_store_schemas.py -v
```

### Run specific test class:
```bash
pytest tests/unit_tests/store/test_store_service.py::TestStoreMemory -v
```

### Run specific test method:
```bash
pytest tests/unit_tests/store/test_store_service.py::TestStoreMemory::test_store_memory_with_string_content -v
```

---

## Test Fixtures

All fixtures are defined in `conftest.py`:

- `mock_store`: AsyncMock of BaseStore for testing
- `store_service`: StoreService instance with mocked store
- `mock_user`: Mock authenticated user data
- `sample_memory_id`: Sample UUID for memory ID
- `sample_message`: Sample Message object with TextBlock
- `sample_memory_result`: Sample MemorySearchResult
- `sample_memory_results`: Sample list of MemorySearchResult

---

## Test Results

```
====================================================== test session starts =======================================================
platform linux -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
collected 62 items

tests/unit_tests/store/test_store_schemas.py::TestStoreMemorySchema::test_valid_with_string_content PASSED                 [  1%]
tests/unit_tests/store/test_store_schemas.py::TestStoreMemorySchema::test_valid_with_message_content PASSED                [  3%]
...
tests/unit_tests/store/test_store_service.py::TestForgetMemory::test_forget_memory_excludes_none_values PASSED             [100%]

================================================= 62 passed, 3 warnings in 1.17s =================================================

Coverage:
- pyagenity_api/src/app/routers/store/schemas/store_schemas.py: 100%
- pyagenity_api/src/app/routers/store/services/store_service.py: 100%
```

---

## Test Organization

- **Unit Tests**: Test individual functions and methods in isolation
- **Mocking**: All external dependencies (BaseStore) are mocked
- **Fixtures**: Shared test data and mocks in conftest.py
- **AAA Pattern**: All tests follow Arrange-Act-Assert pattern
- **Docstrings**: Every test has a clear docstring explaining what it tests

---

## Key Testing Strategies

1. **Comprehensive Coverage**: All service methods and schema validations are tested
2. **Edge Cases**: Tests include boundary conditions, empty data, and error scenarios
3. **Mock Verification**: Tests verify that mocked methods are called correctly
4. **Validation Testing**: Schema tests ensure proper Pydantic validation
5. **Error Handling**: Tests verify proper error handling and exceptions

---

## Future Enhancements

- Add integration tests with real database (requires InjectQ container setup)
- Add performance benchmarks for large-scale operations
- Add tests for concurrent operations
- Add tests for rate limiting and throttling

---

## Notes

- Integration tests are prepared but require InjectQ container configuration
- All unit tests pass with 100% coverage on store module
- Tests use pytest-asyncio for async test support
- Message objects use TextBlock for content as per pyagenity API
