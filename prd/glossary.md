# PRD: Clinical & Technical Standardization Glossary

_MedRAG v2.0 Ubiquitous Terminology Standard_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Clinical Informatics Terms

- **HL7 FHIR R4**: Fast Healthcare Interoperability Resources, Release 4. Standardized JSON REST format for exchanging healthcare electronic records.
- **LOINC**: Logical Observation Identifiers Names and Codes. International standard for identifying laboratory and clinical observations (e.g. `2160-0` for Serum Creatinine).
- **SNOMED-CT**: Systematized Nomenclature of Medicine - Clinical Terms. Comprehensive clinical terminology for diseases, findings, procedures, and anatomy.
- **RxNorm**: Standardized nomenclature for clinical drugs, active ingredients, and administration forms maintained by the National Library of Medicine.
- **Encounter**: An interaction between a patient and healthcare provider(s) for the purpose of providing healthcare service(s).
- **Longitudinal History**: The chronological continuum of patient care events, diagnostic evaluations, and outcomes over time.

---

## 2. Artificial Intelligence & RAG Terms

- **NLI (Natural Language Inference)**: Determining whether a hypothesis is entailed, neutral, or contradicted by a given premise text.
- **DeBERTa**: Decoding-enhanced BERT with disentangled attention. SOTA transformer architecture utilized for NLI claim verification.
- **RRF (Reciprocal Rank Fusion)**: Rank-based algorithm combining score rankings from disparate retrieval systems (vector distance + BM25 lexical).
- **IVF-PQ (Inverted File with Product Quantization)**: Vector index algorithm enabling compressed sub-second similarity search over million-scale vectors.
- **Entailment**: Relationship where the truth of the hypothesis is guaranteed by the truth of the premise chunk.
- **Contradiction**: Relationship where the generated clinical statement directly conflicts with the verified medical literature premise.
- **Faithfulness**: Proportion of generated assertions that are fully entailed by retrieved clinical evidence.

---

## 3. Architecture & Security Terms

- **Hexagonal Architecture (Ports & Adapters)**: Architectural pattern isolating domain business rules from external dependencies through Protocol interfaces.
- **HIPAA Safe Harbor**: Method of de-identification defined under 45 CFR § 164.514(b)(2) removing 18 enumerated personal identifiers.
- **DPDP Act**: Digital Personal Data Protection Act governing personal data sovereignty and consent frameworks.
- **RBAC**: Role-Based Access Control enforcing resource permissions according to assigned clinical roles.
