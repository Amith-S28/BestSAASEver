"""Synthea CSV data ingestion — generates medical PDFs per encounter.

Reads Synthea CSV outputs (patients, encounters, conditions, medications, observations),
generates a realistic PDF report for each encounter, and ingests them into MedRAG.
"""

from __future__ import annotations

import csv
import zipfile
import urllib.request
from collections import defaultdict
from pathlib import Path

from fpdf import FPDF
from rich.console import Console

from medrag.pipeline import MedRAGPipeline

console = Console()

SYNTHEA_SAMPLE_URL = "https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_csv_apr2020.zip"

def safe_text(s: str) -> str:
    """Sanitize text for FPDF Helvetica compatibility and wrap long words."""
    if not s:
        return ""
    # Convert to ascii to avoid FPDF Helvetica encoding errors
    s = str(s).encode('ascii', 'ignore').decode('ascii')
    # FPDF multi_cell crashes on single words longer than page width
    words = []
    for w in s.split():
        while len(w) > 40:
            words.append(w[:40] + "-")
            w = w[40:]
        if w:
            words.append(w)
    return " ".join(words)

def safe_multi_cell(pdf, w, h, text):
    """Safely render a multi_cell, falling back if FPDF crashes on weird characters."""
    try:
        pdf.multi_cell(w, h, text)
    except Exception as e:
        console.print(f"[yellow]Warning: FPDF failed to render text: '{text[:30]}...' ({e})[/yellow]")

class SyntheaIngestor:
    def __init__(self, output_dir: str = "SyntheticData"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = MedRAGPipeline()

    def download_sample_data(self, download_dir: Path) -> Path:
        """Download and extract the Synthea 100-patient sample dataset."""
        download_dir.mkdir(parents=True, exist_ok=True)
        zip_path = download_dir / "synthea_sample.zip"
        extract_dir = download_dir / "csv"

        if not extract_dir.exists():
            console.print(f"[cyan]Downloading Synthea sample data from {SYNTHEA_SAMPLE_URL}[/cyan]")
            urllib.request.urlretrieve(SYNTHEA_SAMPLE_URL, zip_path)
            console.print("[cyan]Extracting ZIP file...[/cyan]")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
        # The zip usually contains a folder called 'csv' or similar inside it.
        # Let's find the folder containing 'patients.csv'
        for path in extract_dir.rglob("patients.csv"):
            return path.parent
            
        return extract_dir

    def _read_csv(self, file_path: Path) -> list[dict]:
        """Read a CSV file into a list of dicts."""
        if not file_path.exists():
            return []
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def process(self, csv_dir: str | None = None, limit_patients: int = 10):
        """Process Synthea CSVs, generate PDFs per encounter, and ingest."""
        if csv_dir is None:
            csv_path = self.download_sample_data(self.output_dir / ".downloads")
        else:
            csv_path = Path(csv_dir)

        if not (csv_path / "patients.csv").exists():
            console.print(f"[red]Error: patients.csv not found in {csv_path}[/red]")
            return

        console.print(f"[cyan]Loading CSV data from {csv_path}...[/cyan]")
        patients = self._read_csv(csv_path / "patients.csv")
        encounters = self._read_csv(csv_path / "encounters.csv")
        conditions = self._read_csv(csv_path / "conditions.csv")
        medications = self._read_csv(csv_path / "medications.csv")
        observations = self._read_csv(csv_path / "observations.csv")

        # Limit patients
        patients = patients[:limit_patients]
        patient_ids = {p["Id"] for p in patients}

        # Index data
        # Encounters by patient
        encounters_by_patient = defaultdict(list)
        for enc in encounters:
            if enc["PATIENT"] in patient_ids:
                encounters_by_patient[enc["PATIENT"]].append(enc)

        # Conditions by encounter
        conditions_by_enc = defaultdict(list)
        for cond in conditions:
            if cond["ENCOUNTER"]:
                conditions_by_enc[cond["ENCOUNTER"]].append(cond)
        
        # Medications by encounter
        medications_by_enc = defaultdict(list)
        for med in medications:
            if med["ENCOUNTER"]:
                medications_by_enc[med["ENCOUNTER"]].append(med)

        # Observations by encounter
        observations_by_enc = defaultdict(list)
        for obs in observations:
            if obs["ENCOUNTER"]:
                observations_by_enc[obs["ENCOUNTER"]].append(obs)

        total_ingested = 0

        for patient in patients:
            pid = patient["Id"]
            first = safe_text(patient.get("FIRST", ""))
            last = safe_text(patient.get("LAST", ""))
            name = f"{first} {last}".strip()
            dob = safe_text(patient.get("BIRTHDATE", "Unknown"))
            gender = safe_text(patient.get("GENDER", "Unknown"))

            # Create patient folder in MedRAG
            folder = self.pipeline.create_folder(name=name, notes=f"Synthea generated. DOB: {dob}")
            
            pat_encounters = encounters_by_patient[pid]
            if not pat_encounters:
                continue
                
            console.print(f"[green]Processing patient: {name} ({len(pat_encounters)} encounters)[/green]")
            
            # Create a physical directory for this patient's PDFs
            patient_dir = self.output_dir / name.replace(" ", "_")
            patient_dir.mkdir(parents=True, exist_ok=True)

            for enc in pat_encounters:
                enc_id = enc["Id"]
                date_str = enc.get("START", enc.get("DATE", "Unknown_Date")).split("T")[0][:10]
                enc_class = safe_text(enc.get("ENCOUNTERCLASS") or "ambulatory")
                reason = safe_text(enc.get("REASONDESCRIPTION") or "Routine Visit")

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, f"Clinical Encounter Report", new_x="LMARGIN", new_y="NEXT", align="C")
                pdf.ln(5)

                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Patient Information", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                safe_multi_cell(pdf, 0, 5, f"Name: {name}\nDOB: {dob}\nGender: {gender}\nPatient ID: {pid}")
                pdf.ln(3)

                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Encounter Details", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                safe_multi_cell(pdf, 0, 5, f"Date: {date_str}\nClass: {enc_class}\nReason: {reason}\nEncounter ID: {enc_id}")
                pdf.ln(3)

                # Conditions
                enc_conds = conditions_by_enc.get(enc_id, [])
                if enc_conds:
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, "Diagnoses / Conditions", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 10)
                    for c in enc_conds:
                        safe_multi_cell(pdf, 0, 5, safe_text(f"- {c.get('DESCRIPTION', 'Unknown')}"))
                    pdf.ln(3)

                # Medications
                enc_meds = medications_by_enc.get(enc_id, [])
                if enc_meds:
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, "Medications Prescribed/Administered", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 10)
                    for m in enc_meds:
                        safe_multi_cell(pdf, 0, 5, safe_text(f"- {m.get('DESCRIPTION', 'Unknown')}"))
                    pdf.ln(3)

                # Observations
                enc_obs = observations_by_enc.get(enc_id, [])
                if enc_obs:
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 8, "Vitals & Lab Observations", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 10)
                    for o in enc_obs:
                        val = safe_text(o.get("VALUE", ""))
                        units = safe_text(o.get("UNITS", ""))
                        safe_multi_cell(pdf, 0, 5, safe_text(f"- {o.get('DESCRIPTION', 'Unknown')}: {val} {units}"))
                    pdf.ln(3)

                pdf_filename = f"{date_str}_{enc_class}.pdf".replace("/", "-").replace(":", "-")
                pdf_path = patient_dir / pdf_filename
                
                # Make sure filename is unique if multiple encounters on same date
                counter = 1
                while pdf_path.exists():
                    pdf_filename = f"{date_str}_{enc_class}_{counter}.pdf".replace("/", "-").replace(":", "-")
                    pdf_path = patient_dir / pdf_filename
                    counter += 1

                pdf.output(str(pdf_path))
                
                # Ingest into MedRAG
                try:
                    self.pipeline.ingest_file(str(pdf_path), folder_id=folder.folder_id)
                    total_ingested += 1
                except Exception as e:
                    console.print(f"[red]Failed to ingest {pdf_path}: {e}[/red]")

        console.print(f"\n[bold green]Synthea integration complete! Ingested {total_ingested} encounter PDFs into MedRAG.[/bold green]")
