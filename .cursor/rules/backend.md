# Cursor Rule: FastAPI Endpoint Design & Async Guidelines

## Rule Invariant
1. All route handlers must be defined as `async def`.
2. Endpoints must never execute blocking synchronous I/O on the main event loop (e.g. `time.sleep()`, synchronous `requests.get()`, heavy CPU inference). Use async libraries (`httpx`, `asyncio.to_thread`).
3. Dependency injection must be used for all port interfaces.
4. Response models must be strictly typed using Pydantic schemas.

### ✅ DO
```python
@router.post("/clinical/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    vector_store: IVectorStore = Depends(get_vector_store),
    user: AuthenticatedUser = Depends(require_scope("query:execute"))
) -> QueryResponse:
    ...
```

### ❌ DON'T
```python
@router.post("/clinical/query")
def execute_query(request: dict):
    time.sleep(2) # Blocking!
```
