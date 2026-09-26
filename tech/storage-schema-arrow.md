# Tech Spec: Apache Arrow Storage Schemas & LanceDB Indexes

_MedRAG v2.0 Columnar In-Process Storage Engine_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Physical Architecture & Table Schemas

LanceDB provides embedded zero-copy vector search powered by Apache Arrow memory-mapped columnar tables.

### 1.1 Table: `clinical_literature`
Stores medical textbook chapters, guideline passages, and clinical literature.

```python
import pyarrow as pa

LITERATURE_SCHEMA = pa.schema([
    pa.field("chunk_id", pa.string(), nullable=False),
    pa.field("tenant_id", pa.string(), nullable=False),          # 'system' for public textbooks
    pa.field("corpus_license_tier", pa.string(), nullable=False), # 'tier1_open' | 'tier2_fairuse' | 'tier3_institutional'
    pa.field("document_id", pa.string(), nullable=False),
    pa.field("title", pa.string(), nullable=False),
    pa.field("chapter", pa.string(), nullable=False),
    pa.field("page_number", pa.int32(), nullable=False),
    pa.field("text_content", pa.string(), nullable=False),
    pa.field("embedding", pa.list_(pa.float32(), 1024), nullable=False), # BGE-Large
    pa.field("snomed_codes", pa.list_(pa.string()), nullable=False),
    pa.field("rxnorm_codes", pa.list_(pa.string()), nullable=False),
    pa.field("loinc_codes", pa.list_(pa.string()), nullable=False),
    pa.field("specialty", pa.string(), nullable=False),
    pa.field("ingested_at", pa.timestamp('us'), nullable=False),
])
```

### 1.2 Table: `patient_timelines`
Stores longitudinal encounter aggregates scoped by tenant and clinic.

```python
TIMELINES_SCHEMA = pa.schema([
    pa.field("patient_id", pa.string(), nullable=False),
    pa.field("tenant_id", pa.string(), nullable=False),
    pa.field("clinic_id", pa.string(), nullable=False),
    pa.field("demographics_json", pa.string(), nullable=False),
    pa.field("timeline_json", pa.string(), nullable=False),       # Full serialized ClinicalEncounter list
    pa.field("encounter_count", pa.int32(), nullable=False),
    pa.field("last_encounter_at", pa.timestamp('us'), nullable=False),
    pa.field("created_at", pa.timestamp('us'), nullable=False),
    pa.field("updated_at", pa.timestamp('us'), nullable=False),
])
```

### 1.3 Table: `audit_log`
Immutable clinical audit log with rolling hash verification.

```python
AUDIT_LOG_SCHEMA = pa.schema([
    pa.field("log_id", pa.string(), nullable=False),
    pa.field("tenant_id", pa.string(), nullable=False),
    pa.field("user_id", pa.string(), nullable=False),
    pa.field("action", pa.string(), nullable=False),
    pa.field("entity_type", pa.string(), nullable=False),
    pa.field("entity_id", pa.string(), nullable=False),
    pa.field("details_json", pa.string(), nullable=False),
    pa.field("trace_id", pa.string(), nullable=False),
    pa.field("prev_hash", pa.string(), nullable=False),          # Rolling cryptographic hash chain
    pa.field("curr_hash", pa.string(), nullable=False),
    pa.field("occurred_at", pa.timestamp('us'), nullable=False),
])
```

---

## 2. Indexing Strategy

1. **Vector Index**: LanceDB `IVF-PQ` (Inverted File with Product Quantization) computed on `embedding` column using Cosine distance metric.
2. **Lexical Index**: Tantivy full-text index on `text_content` with English stemming and medical stopword suppression.
3. **Compound Filters**: Scalar B-Tree index on `tenant_id` and `clinic_id` for zero-overhead tenant partitioning.
