# Cursor Rule: Authentication & Token Validation Standards

## Rule Invariant
1. Raw API keys must never be stored. Use Argon2id hashing with unique random salts.
2. JWT tokens must validate expiration (`exp`) and signature before decoding claims.
3. Every protected route must declare explicit scope dependencies via `require_scope("...")`.

### ✅ DO
```python
@router.delete("/patients/{id}", dependencies=[Depends(require_scope("patient:delete"))])
async def delete_patient(id: str, ...):
    ...
```
