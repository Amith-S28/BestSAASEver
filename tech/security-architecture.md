# Tech Spec: Security Architecture, Authentication & Encryption

_MedRAG v2.0 Enterprise Security Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Authentication Layer & Credential Management

### 1.1 Dual Authentication Mechanisms
1. **Interactive Session JWTs**: Short-lived JSON Web Tokens signed with HS256/RS256 containing `user_id`, `tenant_id`, `clinic_id`, `role`, and `scopes`.
2. **Programmatic API Keys**: Formatted as `mrk_<random_hex_32>`. Keys are hashed using **Argon2id** (memory cost 64MB, 3 iterations) before database persistence.

### 1.2 Tenant Context Middleware
Every incoming request is processed by `TenantScopeMiddleware`:
- Extracts and validates authorization header.
- Sets thread-local / async context var: `current_tenant_id` and `current_user`.
- Rejects any attempt to specify tenant via query parameters or unvalidated request headers.

---

## 2. Multi-Tenant Database Isolation

In LanceDB, tenant isolation is enforced at the repository adapter level. Every table query automatically appends compound tenant constraints:

```python
# LanceDB Repository Layer
def build_tenant_predicate(tenant_id: str, clinic_id: Optional[str] = None) -> str:
    predicate = f"tenant_id = '{tenant_id}'"
    if clinic_id:
        predicate += f" AND clinic_id = '{clinic_id}'"
    return predicate

# Any query lacking tenant_id throws TenantIsolationViolationException immediately.
```

---

## 3. Cryptographic Storage & Key Management

- **Volume Encryption**: Operating system level BitLocker or LUKS with AES-256 for persistent LanceDB directories.
- **Salt Management**: HMAC-SHA256 salt for PHI tokenization is loaded from environment secrets and never committed to source control.
