# Cursor Rule: Test Isolation & Port Mocking Rules

## Rule Invariant
1. Domain unit tests must achieve 100% code and branch coverage.
2. In application and integration tests, all port interfaces (`IVectorStore`, `INLIVerifier`, `ILanguageModel`) must be mocked using `unittest.mock` or typed fake adapters.
3. Tests must never share mutable state across executions; each test instantiates clean fixtures.

### ✅ DO
```python
@pytest.fixture
def mock_vector_store():
    store = MagicMock(spec=IVectorStore)
    store.query_hybrid.return_value = []
    return store
```
