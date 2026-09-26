# Cursor Rule: Cursor-Based Pagination Standards

## Rule Invariant
1. All listing endpoints (`/patients`, `/queries`, `/audit/log`) must use opaque cursor-based pagination.
2. Default page limit is 25 items; maximum allowable limit is 100 items.
3. Response envelopes must include `items`, `cursor`, `has_more`, and `total_count`.

### ✅ DO
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    cursor: Optional[str]
    has_more: bool
    total_count: int
```
