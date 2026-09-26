# PRD: Non-Functional Requirements & Performance SLAs

_MedRAG v2.0 Operational & Quality Engineering Metrics_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Latency & Throughput Targets

| Operation | Metric | Target SLA | Degraded Threshold |
|---|---|---|---|
| **Hybrid Retrieval (LanceDB + Tantivy)** | Latency p95 | < 8ms | > 20ms |
| **Cross-Encoder Re-Ranking (MiniLM)** | Latency p95 | < 50ms | > 100ms |
| **Clinical Synthesis Time-to-First-Token (TTFT)** | Latency p95 | < 800ms | > 2,000ms |
| **Total Query Synthesis & Verification** | Latency p95 | < 3,500ms | > 6,000ms |
| **FHIR Bundle Ingestion (10MB JSON)** | Ingestion Time | < 3,000ms | > 8,000ms |
| **Digital Lab PDF Parsing (per page)** | Parse Time | < 500ms | > 1,500ms |

---

## 2. Resource Budgets & Footprint

- **Idle RAM Overhead**: 0 MB for vector tables (LanceDB disk memory-mapping).
- **VRAM Allocation (Inference Stack)**:
  - Embedding (`bge-large-en-v1.5`): ~1.3 GB (or CPU inference via ONNX Runtime @ 12ms).
  - Reranker (`ms-marco-MiniLM-L-6-v2`): ~50 MB.
  - NLI Verifier (`deberta-v3-large-mnli`): ~1.3 GB.
  - Synthesis Model (`Qwen2.5-32B` quantized Q4_K_M): ~18 GB.
  - Total Minimum VRAM for full GPU stack: 24 GB (RTX 3090/4090 or A10G).
  - Minimum CPU Fallback footprint: 16 GB system RAM.

---

## 3. Reliability & Availability

- **Platform Uptime**: 99.9% for SaaS API endpoints.
- **Failover SLA**: Automatic fallback from primary vLLM endpoint to secondary LM Studio/Ollama endpoint within 2,000ms.
- **Data Durability**: Zero data loss on power disruption (LanceDB atomic commit semantics).
