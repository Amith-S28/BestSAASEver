"""Clinical prompt composition and token budgeting service."""

from typing import List, Optional
from medrag.domain.literature import MedicalChunk
from medrag.domain.patient import PatientTimeline


class ClinicalPromptComposer:
    """Composes grounded clinical prompts with patient history and cited literature passages."""

    SYSTEM_INSTRUCTION = (
        "You are MedRAG, an institutional-grade clinical AI intelligence assistant.\n"
        "Your task is to synthesize clinical evidence for licensed healthcare providers.\n"
        "STRICT MANDATE:\n"
        "1. Every factual clinical claim MUST be accompanied by an inline citation anchor (e.g. [^1], [^2])\n"
        "   referencing the retrieved medical literature evidence.\n"
        "2. Do NOT invent drug interactions or recommendations not directly entailed by the provided evidence.\n"
        "3. Highlight abnormal laboratory trajectories and flag critical findings prominently."
    )

    def format_patient_context(self, timeline: Optional[PatientTimeline]) -> str:
        """Format structured patient timeline into concise clinical context."""
        if not timeline or timeline.encounter_count() == 0:
            return "No prior electronic health record encounters found for this patient."

        lines = [
            f"Patient Demographic: {timeline.demographics.get('gender', 'unknown')}, Age {timeline.demographics.get('age', 'unknown')}",
            f"Total Recorded Encounters: {timeline.encounter_count()}",
        ]

        # Active medications
        active_meds = timeline.active_medications()
        if active_meds:
            med_strs = [f"{m.drug_name} ({m.dosage})" for m in active_meds]
            lines.append(f"Active Medications: {', '.join(med_strs)}")

        # Critical observations
        crit_obs = timeline.all_critical_observations()
        if crit_obs:
            crit_strs = [f"{o.display_name}: {o.numeric_value} {o.unit} [{o.flag.value}]" for o in crit_obs]
            lines.append(f"CRITICAL LAB FLAGS: {'; '.join(crit_strs)}")

        # Latest encounter
        latest = timeline.latest_encounter()
        if latest:
            lines.append(f"Latest Encounter ({latest.encounter_type}): {latest.chief_complaint or 'Routine evaluation'}")
            abnormal = latest.abnormal_observations()
            if abnormal:
                ab_strs = [f"{o.display_name}: {o.numeric_value} {o.unit} (Ref: {o.reference_low}-{o.reference_high})" for o in abnormal]
                lines.append(f"Latest Abnormal Labs: {', '.join(ab_strs)}")

        return "\n".join(lines)

    def format_evidence_passages(self, chunks: List[MedicalChunk]) -> str:
        """Format retrieved literature chunks with citation indices."""
        if not chunks:
            return "No literature passages retrieved."

        passages = []
        for idx, chunk in enumerate(chunks, start=1):
            header = f"[^{idx}] {chunk.title} - {chunk.chapter}, p. {chunk.page_number} [{chunk.specialty}]"
            passages.append(f"{header}\n{chunk.text_content}")

        return "\n\n".join(passages)

    def compose_prompt(
        self,
        query_text: str,
        timeline: Optional[PatientTimeline],
        evidence_chunks: List[MedicalChunk],
    ) -> str:
        """Construct full prompt string within token budget."""
        patient_str = self.format_patient_context(timeline)
        evidence_str = self.format_evidence_passages(evidence_chunks)

        prompt = (
            f"{self.SYSTEM_INSTRUCTION}\n\n"
            f"--- PATIENT LONGITUDINAL CONTEXT ---\n"
            f"{patient_str}\n\n"
            f"--- VERIFIED MEDICAL LITERATURE EVIDENCE ---\n"
            f"{evidence_str}\n\n"
            f"--- CLINICAL INQUIRY ---\n"
            f"Question: {query_text}\n\n"
            f"Provide an evidence-grounded clinical synthesis:"
        )
        return prompt
