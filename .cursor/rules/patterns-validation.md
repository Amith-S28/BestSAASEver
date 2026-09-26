# Cursor Rule: Request DTO Validation & Sanitization

## Rule Invariant
1. All client inputs must be validated at the API boundary using Pydantic V2 schemas.
2. Clinical queries must enforce bounds: min 3 characters, max 1,000 characters.
3. String inputs must be stripped of leading/trailing whitespace and control characters.

### ✅ DO
```python
class QueryRequest(BaseModel):
    query_text: str = Field(..., min_length=3, max_length=1000)
    patient_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    stream: bool = True

    @field_validator("query_text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return v.strip()
```
