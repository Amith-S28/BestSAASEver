# Tech Spec: Frontend Architecture (Next.js 15 & React 19)

_MedRAG v2.0 Clinician Workspace Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Architectural Stack

- **Framework**: Next.js 15 (App Router) with React 19 Server Components.
- **State Management**: Zustand for interactive streaming state; React Query for server cache.
- **Styling**: Vanilla CSS Modules with design tokens from UI/UX Pro Max.
- **Streaming Client**: Native `fetch` with `ReadableStream` reader parsing SSE events.

---

## 2. Core UI Component Hierarchy

```text
ClinicianDashboard
├── TopNavigation (Tenant selector, user profile, quota indicator)
├── PatientSidebar (Search, filter, recent patients)
└── WorkspacePanel
    ├── PatientTimelineExplorer
    │   ├── EncounterSwimlane (Inpatient, ER, Ambulatory)
    │   ├── LabTrendSparklines (LOINC time-series chart)
    │   └── MedicationSchedule (Active vs Completed)
    ├── StreamingSynthesisPanel
    │   ├── PromptInputBar
    │   ├── StreamingResponseViewer
    │   │   └── SentenceClaim (Color-coded verification status)
    │   └── SafetyAlertBanner (Visible if claims redacted)
    └── EvidenceDrawer (Slide-out panel)
        ├── MedicalPassageViewer (Highlighted excerpt)
        ├── SourceMetadataCard (Harrison's, Chapter, Page)
        └── CMOOverrideButton (For CMO role only)
```
