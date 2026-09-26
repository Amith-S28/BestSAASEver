# Cursor Rules Index & Machine Verification Guidelines

_MedRAG v2.0 AI Assistant & Developer Governance Rules_

---

## Rule Directory Index

| Rule File | Domain / Focus Area | Hard Enforcement Mechanism |
|---|---|---|
| `architecture.md` | Hexagonal boundary & port protocols | `scripts/lint_domain_imports.py` |
| `backend.md` | FastAPI endpoint design & async lifecycles | Ruff static analysis |
| `frontend.md` | Next.js 15, React Server Components & UI/UX tokens | Pre-commit linter |
| `patterns-domain-isolation.md` | Pure domain entities & immutability | AST boundary linter |
| `patterns-error-handling.md` | Banned generic exceptions & ClinicalException | AST & Ruff custom rules |
| `patterns-storage-scoping.md` | Mandatory compound `tenant_id` queries | Repository assertions |
| `patterns-nli-verification.md` | Claim decomposition & contradiction redact | Automated CI tests |
| `patterns-logging-audit.md` | Structured JSON logging & PHI masking | Code review & tests |
| `patterns-background-jobs.md` | Idempotency, retries & distributed locks | ARQ test harness |
| `patterns-api-streaming.md` | SSE chunking & error recovery | SSE integration tests |
| `patterns-security.md` | Argon2id keys & JWT scope extraction | Security sweep |
| `patterns-pagination.md` | Cursor-based pagination standards | API contract tests |
| `patterns-validation.md` | DTO validation & bounds checking | Pydantic strict mode |
| `testing.md` | 100% domain coverage & port mocking | pytest quality gate |
