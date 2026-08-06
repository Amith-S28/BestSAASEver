"""Medical document downloader — fetches PDFs from NIH PMC and generates synthetic docs.

Downloads open-access medical articles from PubMed Central, organizes them
into simulated family folders by medical topic, and auto-ingests into MedRAG.

If PMC downloads fail or are slow, generates synthetic lab reports as fallback.

Usage:
    medrag download --count 10
    medrag download --count 50 --clean
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

import httpx

from medrag.config import settings

# ── PMC Open Access URLs ───────────────────────────────────────────────────

PMC_OA_LIST_URL = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/oa_comm_use_file_list.txt"
PMC_PDF_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles/"

# Cache the OA listing for 24 hours
_OA_LIST_CACHE_FILE = "oa_comm_use_file_list.txt"
_OA_LIST_CACHE_MAX_AGE_HOURS = 24

# ── Category → Folder Mapping ──────────────────────────────────────────────

CATEGORY_FOLDERS: dict[str, dict[str, str]] = {
    # Me — metabolic / endocrine / general
    "metabolic": {"name": "Me", "relationship": "self", "key": "me"},
    "endocrine": {"name": "Me", "relationship": "self", "key": "me"},
    "diabetes": {"name": "Me", "relationship": "self", "key": "me"},
    "thyroid": {"name": "Me", "relationship": "self", "key": "me"},
    "cholesterol": {"name": "Me", "relationship": "self", "key": "me"},
    "hyperlipidemia": {"name": "Me", "relationship": "self", "key": "me"},
    "hemochromatosis": {"name": "Me", "relationship": "self", "key": "me"},
    # Mom — women's health / oncology / autoimmune
    "breast cancer": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "oncology": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "osteoporosis": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "autoimmune": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "lupus": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "celiac": {"name": "Mom", "relationship": "mother", "key": "mom"},
    "ovarian": {"name": "Mom", "relationship": "mother", "key": "mom"},
    # Dad — cardiovascular / men's health
    "cardiovascular": {"name": "Dad", "relationship": "father", "key": "dad"},
    "heart": {"name": "Dad", "relationship": "father", "key": "dad"},
    "hypertension": {"name": "Dad", "relationship": "father", "key": "dad"},
    "prostate": {"name": "Dad", "relationship": "father", "key": "dad"},
    "coronary": {"name": "Dad", "relationship": "father", "key": "dad"},
    "cardiomyopathy": {"name": "Dad", "relationship": "father", "key": "dad"},
    "atrial": {"name": "Dad", "relationship": "father", "key": "dad"},
    # Sister — neurological / mental health
    "neurology": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "epilepsy": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "depression": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "mental health": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "adhd": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "bipolar": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "schizophrenia": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "alzheimer": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    "parkinson": {"name": "Sister", "relationship": "sibling", "key": "sister"},
    # Me (general) — respiratory / allergy / pulmonary
    "respiratory": {"name": "Me", "relationship": "self", "key": "me"},
    "asthma": {"name": "Me", "relationship": "self", "key": "me"},
    "copd": {"name": "Me", "relationship": "self", "key": "me"},
    "allergy": {"name": "Me", "relationship": "self", "key": "me"},
    "pulmonary": {"name": "Me", "relationship": "self", "key": "me"},
    "cystic fibrosis": {"name": "Me", "relationship": "self", "key": "me"},
    "alpha-1": {"name": "Me", "relationship": "self", "key": "me"},
}

# Folder display order
FOLDER_ORDER = ["me", "mom", "dad", "sister"]


@dataclass(frozen=True)
class PmcArticle:
    """A single PMC open-access article."""
    pmcid: str
    doi: str = ""
    citation: str = ""
    url: str = ""


# ── PMC List Fetching ──────────────────────────────────────────────────────


def download_pmc_list(cache_dir: Path | None = None) -> list[PmcArticle]:
    """Download and parse the PMC OA file list.

    The file is tab-delimited: File|PMCID|DOI|Citation
    Caches locally for 24 hours to avoid repeated downloads.
    """
    if cache_dir is None:
        cache_dir = Path(settings.raw_dir) / "downloads"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / _OA_LIST_CACHE_FILE

    # Check cache
    if cache_file.exists():
        age_hours = (datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_file.stat().st_mtime, tz=timezone.utc
        )).total_seconds() / 3600
        if age_hours < _OA_LIST_CACHE_MAX_AGE_HOURS:
            print(f"[medrag:download] Using cached PMC list ({age_hours:.0f}h old)")
            return _parse_pmc_list(cache_file.read_text())

    # Download fresh
    print("[medrag:download] Downloading PMC open-access article list...")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(PMC_OA_LIST_URL, follow_redirects=True)
            resp.raise_for_status()
            cache_file.write_bytes(resp.content)
            print(f"[medrag:download] Cached PMC list ({len(resp.content):,} bytes)")
            return _parse_pmc_list(resp.text)
    except httpx.HTTPError as e:
        print(f"[medrag:download] [FAIL] Failed to download PMC list: {e}")
        if cache_file.exists():
            print("[medrag:download] Using stale cache as fallback")
            return _parse_pmc_list(cache_file.read_text())
        return []


def _parse_pmc_list(text: str) -> list[PmcArticle]:
    """Parse the tab-delimited PMC OA file list."""
    articles: list[PmcArticle] = []
    for line in text.strip().splitlines():
        if line.startswith("File") or line.startswith("#"):
            continue  # skip header
        parts = line.strip().split("\t")
        if len(parts) < 4:
            continue
        articles.append(PmcArticle(
            pmcid=parts[1].strip(),
            doi=parts[2].strip(),
            citation=parts[3].strip(),
            url=parts[0].strip(),
        ))
    return articles


# ── Category Filtering ─────────────────────────────────────────────────────


def filter_medical_articles(
    articles: list[PmcArticle],
    limit: int = 50,
) -> list[tuple[PmcArticle, str]]:
    """Filter articles by medical categories and assign folders.

    Returns list of (article, folder_key) tuples.
    """
    matched: list[tuple[PmcArticle, str]] = []
    folder_counts: dict[str, int] = {k: 0 for k in FOLDER_ORDER}
    max_per_folder = max(1, limit // len(FOLDER_ORDER))

    # Build keyword patterns for each folder
    folder_keywords: dict[str, list[re.Pattern]] = {}
    for keyword, folder_info in CATEGORY_FOLDERS.items():
        key = folder_info["key"]
        if key not in folder_keywords:
            folder_keywords[key] = []
        folder_keywords[key].append(re.compile(re.escape(keyword), re.IGNORECASE))

    for article in articles:
        if len(matched) >= limit:
            break

        citation_lower = article.citation.lower()

        # Try each folder's keywords
        assigned_key: str | None = None
        for key, patterns in folder_keywords.items():
            if folder_counts[key] >= max_per_folder:
                continue
            if any(p.search(citation_lower) for p in patterns):
                assigned_key = key
                break

        if assigned_key is None:
            # Round-robin assign to least-filled folder
            min_key = min(folder_counts, key=folder_counts.get)  # type: ignore[arg-type]
            if folder_counts[min_key] >= max_per_folder:
                continue  # all folders full
            assigned_key = min_key

        folder_counts[assigned_key] += 1
        matched.append((article, assigned_key))

    print(f"[medrag:download] Matched {len(matched)} articles across folders: {folder_counts}")
    return matched


def get_folder_info(folder_key: str) -> dict[str, str]:
    """Get folder name and relationship from folder key."""
    for cat, info in CATEGORY_FOLDERS.items():
        if info["key"] == folder_key:
            return {"name": info["name"], "relationship": info["relationship"]}
    return {"name": folder_key.title(), "relationship": "other"}


# ── PDF Download ────────────────────────────────────────────────────────────


def download_pdf(
    pmcid: str,
    dest_dir: Path,
    client: httpx.Client,
) -> Path | None:
    """Download a single PDF from PMC.

    PMC serves PDFs at: https://www.ncbi.nlm.nih.gov/pmc/articles/{PMCID}/pdf/
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"{pmcid}.pdf"

    if dest_file.exists():
        print(f"[medrag:download]   [OK] Already cached: {pmcid}")
        return dest_file

    # Try PDF URL
    pdf_url = f"{PMC_PDF_BASE}{pmcid}/pdf/"
    try:
        resp = client.get(pdf_url, follow_redirects=True, timeout=60.0)
        if resp.status_code == 200 and "pdf" in resp.headers.get("content-type", "").lower():
            dest_file.write_bytes(resp.content)
            print(f"[medrag:download]   [OK] Downloaded {pmcid} ({len(resp.content):,} bytes)")
            return dest_file
    except httpx.HTTPError:
        pass

    # Fallback: try the article page and look for PDF link
    article_url = f"{PMC_PDF_BASE}{pmcid}/"
    try:
        resp = client.get(article_url, follow_redirects=True, timeout=60.0)
        if resp.status_code != 200:
            print(f"[medrag:download]   [FAIL] {pmcid}: HTTP {resp.status_code}")
            return None
        # Check if we got a PDF (sometimes direct links work)
        if "pdf" in resp.headers.get("content-type", "").lower():
            dest_file.write_bytes(resp.content)
            print(f"[medrag:download]   [OK] Downloaded {pmcid} (via article page)")
            return dest_file
    except httpx.HTTPError as e:
        print(f"[medrag:download]   [FAIL] {pmcid}: {e}")
        return None

    print(f"[medrag:download]   [FAIL] {pmcid}: No PDF found")
    return None


# ── Synthetic PDF Generation ───────────────────────────────────────────────


def generate_synthetic_docs(
    dest_dir: Path,
    folder_key: str,
    count: int = 5,
) -> list[Path]:
    """Generate synthetic medical PDF documents as fallback test data."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("[medrag:download] fpdf2 not installed. Run: pip install fpdf2")
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    folder_info = get_folder_info(folder_key)
    generated: list[Path] = []

    # Template lab reports per folder
    templates = _get_synthetic_templates(folder_key, folder_info["name"])

    for i in range(count):
        base_template = templates[i % len(templates)]
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        doc_num = i + 1
        title = f"{base_template['title']} (Report #{doc_num})"
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 10)

        for section_title, section_text in base_template["sections"].items():
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, section_title, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, f"{section_text}\n[Document Ref: PDF-MED-{doc_num:03d}]")
            pdf.ln(2)

        filename = f"synthetic_{folder_key}_{doc_num:03d}.pdf"
        filepath = dest_dir / filename
        pdf.output(str(filepath))
        generated.append(filepath)

    print(f"[medrag:download]   Generated {len(generated)} synthetic PDFs for {folder_info['name']}")
    return generated


def _get_synthetic_templates(folder_key: str, name: str) -> list[dict]:
    """Return synthetic document templates for each folder category."""
    now = "2026-06-07"

    if folder_key == "me":
        return [
            {"title": f"Comprehensive Metabolic Panel -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1990-03-15 | ID: MR-001",
                "Lab Results": (
                    f"Date: {now}\n"
                    "Glucose: 142 mg/dL (Ref: 70-100) -- ELEVATED\n"
                    "HbA1c: 7.2% (Ref: <5.7%) -- ELEVATED -- Type 2 Diabetes indication\n"
                    "Total Cholesterol: 248 mg/dL (Ref: <200) -- ELEVATED\n"
                    "LDL-C: 162 mg/dL (Ref: <100) -- ELEVATED\n"
                    "HDL-C: 38 mg/dL (Ref: >40) -- LOW\n"
                    "Triglycerides: 220 mg/dL (Ref: <150) -- ELEVATED\n"
                    "TSH: 5.8 mIU/L (Ref: 0.4-4.0) -- ELEVATED -- Subclinical hypothyroidism\n"
                    "Free T4: 0.7 ng/dL (Ref: 0.8-1.8) -- LOW\n"
                    "Ferritin: 320 ng/mL (Ref: 12-300) -- ELEVATED\n"
                    "ALT: 52 U/L (Ref: 7-56) -- Borderline\n"
                    "AST: 48 U/L (Ref: 10-40) -- ELEVATED"
                ),
                "Assessment": (
                    "1. Type 2 Diabetes Mellitus -- HbA1c 7.2%, uncontrolled\n"
                    "2. Mixed Hyperlipidemia -- LDL 162, TG 220, HDL low\n"
                    "3. Subclinical Hypothyroidism -- TSH 5.8, consider levothyroxine\n"
                    "4. Possible Hemochromatosis -- Ferritin 320, check HFE genotype\n"
                    "5. Mild hepatic inflammation -- monitor ALT/AST"
                ),
                "Medications": "Metformin 1000mg BID, Atorvastatin 40mg QD, Levothyroxine 25mcg QD",
            }},
            {"title": f"Thyroid Follow-Up -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1990-03-15 | ID: MR-001",
                "Lab Results": (
                    f"Date: 2026-05-01\n"
                    "TSH: 6.2 mIU/L (Ref: 0.4-4.0) -- ELEVATED\n"
                    "TPO Antibodies: 342 IU/mL (Ref: <35) -- STRONGLY POSITIVE\n"
                    "TgAb: 156 IU/mL (Ref: <40) -- POSITIVE\n"
                    "Free T3: 2.1 pg/mL (Ref: 2.3-4.2) -- LOW\n"
                    "Free T4: 0.65 ng/dL (Ref: 0.8-1.8) -- LOW"
                ),
                "Assessment": (
                    "1. Hashimoto's Thyroiditis -- confirmed by elevated TPO and TgAb\n"
                    "2. Overt Hypothyroidism -- TSH >6 with low Free T4\n"
                    "3. Autoimmune thyroid disease -- increased risk for other autoimmune conditions\n"
                    "4. Family screening recommended -- first-degree relatives at 5-10x risk"
                ),
                "Plan": "Increase levothyroxine to 50mcg QD. Recheck TSH in 6 weeks. Screen for celiac and B12 deficiency.",
            }},
            {"title": f"Annual Physical Exam -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1990-03-15 | ID: MR-001",
                "Vitals": "BP: 138/88 mmHg | BMI: 31.2 | HR: 78 | Temp: 98.4°F",
                "Lab Results": (
                    f"Date: 2026-01-10\n"
                    "Fasting Glucose: 128 mg/dL -- ELEVATED\n"
                    "HbA1c: 6.8% -- Prediabetes/Diabetes range\n"
                    "Creatinine: 1.1 mg/dL (Ref: 0.7-1.3)\n"
                    "eGFR: 92 mL/min -- Normal\n"
                    "ALT: 45 U/L -- Borderline\n"
                    "Vitamin D: 18 ng/mL (Ref: 30-100) -- DEFICIENT\n"
                    "B12: 280 pg/mL (Ref: 200-900) -- Low-normal"
                ),
                "Assessment": "1. Pre-diabetes/Early T2DM  2. Vitamin D deficiency  3. Overweight/Obese  4. Family history: Mother -- breast cancer, Father -- MI at age 58",
            }},
        ]
    elif folder_key == "mom":
        return [
            {"title": f"Mammogram & Breast Health -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1958-07-22 | ID: MR-002",
                "Mammogram Results": (
                    f"Date: {now}\n"
                    "BIRADS Category: 4 -- Suspicious abnormality, biopsy recommended\n"
                    "Finding: 1.2 cm irregular mass, upper outer quadrant, left breast\n"
                    "Architecture distortion present\n"
                    "Microcalcifications: Clustered, new since prior study"
                ),
                "Risk Factors": (
                    "1. Age 67 -- increased risk with age\n"
                    "2. BRCA testing: BRCA2 variant of uncertain significance identified\n"
                    "3. First-degree relative (daughter) -- screening recommended\n"
                    "4. Prior atypical hyperplasia on biopsy (2022)\n"
                    "5. Lifetime risk estimate: elevated per Gail model"
                ),
                "Assessment": "BIRADS 4 -- core needle biopsy recommended. Genetic counseling for BRCA2 VUS.",
            }},
            {"title": f"Bone Density Scan -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1958-07-22 | ID: MR-002",
                "DEXA Results": (
                    f"Date: 2025-11-15\n"
                    "Lumbar Spine L1-L4: T-score -2.8 -- OSTEOPOROSIS\n"
                    "Left Femoral Neck: T-score -2.3 -- OSTEOPOROSIS\n"
                    "Total Left Hip: T-score -2.1 -- OSTEOPOROSIS\n"
                    "FRAX 10-year hip fracture risk: 7.2%\n"
                    "FRAX 10-year major osteoporotic: 22%"
                ),
                "Assessment": "Osteoporosis -- T-score <=-2.5 at multiple sites. High fracture risk per FRAX.",
                "Medications": "Alendronate 70mg weekly, Calcium 1200mg daily, Vitamin D 2000IU daily",
            }},
            {"title": f"Autoimmune Panel -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1958-07-22 | ID: MR-002",
                "Lab Results": (
                    f"Date: 2026-03-20\n"
                    "ANA: 1:640 speckled pattern -- STRONGLY POSITIVE\n"
                    "Anti-dsDNA: 45 IU/mL (Ref: <10) -- POSITIVE\n"
                    "Complement C3: 62 mg/dL (Ref: 90-180) -- LOW\n"
                    "Complement C4: 10 mg/dL (Ref: 10-40) -- Low-normal\n"
                    "ESR: 38 mm/hr (Ref: 0-20) -- ELEVATED\n"
                    "CRP: 1.8 mg/dL (Ref: <0.5) -- ELEVATED\n"
                    "Anti-Smith: Positive\n"
                    "Rheumatoid Factor: 28 IU/mL (Ref: <20) -- Borderline elevated"
                ),
                "Assessment": "1. Systemic Lupus Erythematosus (SLE) -- 4/11 ACR criteria met\n2. Active disease -- low complement, elevated inflammatory markers\n3. First-degree relatives at 5-8x increased risk\n4. Monitor renal function quarterly",
            }},
        ]
    elif folder_key == "dad":
        return [
            {"title": f"Cardiac Evaluation -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1955-11-08 | ID: MR-003",
                "Echocardiogram": (
                    f"Date: {now}\n"
                    "LVEF: 52% -- Mildly reduced\n"
                    "Left Ventricular Wall: 13mm -- Mild hypertrophy\n"
                    "Septal thickness: 14mm\n"
                    "Diastolic function: Grade 1 (impaired relaxation)\n"
                    "Mild mitral regurgitation\n"
                    "Left atrial enlargement: 4.5 cm"
                ),
                "Lab Results": (
                    f"Date: {now}\n"
                    "Troponin I: <0.04 ng/mL -- Normal\n"
                    "BNP: 285 pg/mL (Ref: <100) -- ELEVATED\n"
                    "LDL-C: 158 mg/dL (Ref: <100) -- ELEVATED\n"
                    "HDL-C: 32 mg/dL (Ref: >40) -- LOW\n"
                    "Total Cholesterol: 262 mg/dL -- ELEVATED\n"
                    "CRP-hs: 3.2 mg/L (Ref: <1.0) -- ELEVATED -- Cardiovascular risk marker"
                ),
                "Assessment": "1. CAD -- Prior MI (2019), current stable angina  2. Hypertensive heart disease  3. Diastolic dysfunction  4. Familial hypercholesterolemia suspected -- LDL >190 + family history",
            }},
            {"title": f"Hypertension Management -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1955-11-08 | ID: MR-003",
                "Blood Pressure Log": (
                    f"Period: May 2026\n"
                    "Average BP: 152/94 mmHg -- Stage 2 Hypertension\n"
                    "Home readings: Range 140-165/85-100\n"
                    "Morning surge: 158/96 average\n"
                    "Ambulatory 24hr: Mean 148/91, Daytime 152/94, Nighttime 138/82\n"
                    "Non-dipper pattern noted"
                ),
                "Current Medications": "Lisinopril 20mg QD, Amlodipine 10mg QD, Hydrochlorothiazide 25mg QD",
                "Assessment": (
                    "1. Resistant hypertension on 3 medications\n"
                    "2. Non-dipper pattern -- increased cardiovascular risk\n"
                    "3. First-degree relatives: 2-4x increased risk of hypertension\n"
                    "4. Consider adding spironolactone or referral to HTN specialist"
                ),
            }},
            {"title": f"Prostate Screening -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1955-11-08 | ID: MR-003",
                "Lab Results": (
                    f"Date: 2026-04-10\n"
                    "PSA Total: 6.8 ng/mL (Ref: <4.0 for age 60+) -- ELEVATED\n"
                    "PSA Free: 1.1 ng/mL\n"
                    "Free/Total Ratio: 16% (Ref: >25%) -- LOW -- concerning\n"
                    "PSA Velocity: 1.2 ng/mL/year -- ELEVATED"
                ),
                "Assessment": "Elevated PSA with low free/total ratio. Prostate biopsy recommended. Family history of prostate cancer increases pre-test probability.",
            }},
        ]
    elif folder_key == "sister":
        return [
            {"title": f"EEG & Neurology Consult -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1993-05-19 | ID: MR-004",
                "EEG Results": (
                    f"Date: {now}\n"
                    "Background: 8-9 Hz alpha rhythm, well-organized\n"
                    "Intermittent: Generalized 3-4 Hz spike-and-wave discharges\n"
                    "Duration of discharges: 2-4 seconds\n"
                    "Activated by: Hyperventilation, photic stimulation at 14 Hz\n"
                    "Impression: Abnormal -- consistent with generalized epilepsy"
                ),
                "Assessment": (
                    "1. Generalized epilepsy -- Juvenile Myoclonic Epilepsy pattern\n"
                    "2. First-degree relatives: 2-4x increased risk\n"
                    "3. MRI Brain: Normal -- no structural cause identified\n"
                    "4. Genetic testing: Consider SCN1A, GABRG2 panel"
                ),
                "Medications": "Levetiracetam 750mg BID",
            }},
            {"title": f"Psychiatric Evaluation -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1993-05-19 | ID: MR-004",
                "PHQ-9 Score": "18/27 -- Moderately Severe Depression",
                "GAD-7 Score": "14/21 -- Moderate Anxiety",
                "Assessment": (
                    "1. Major Depressive Disorder -- recurrent, current episode moderate-severe\n"
                    "2. Generalized Anxiety Disorder -- comorbid with MDD\n"
                    "3. Family history positive: maternal aunt -- bipolar disorder\n"
                    "4. First-degree relatives: 2-3x risk for depression, 5-10x for bipolar\n"
                    "5. Risk assessment: No active suicidal ideation, passive ideation reported"
                ),
                "Medications": "Sertraline 100mg QD, Buspirone 10mg BID",
            }},
            {"title": f"ADHD Assessment -- {name}", "sections": {
                "Patient": f"Name: {name} | DOB: 1993-05-19 | ID: MR-004",
                "ASRS v1.1": "Score 14/18 -- Highly consistent with ADHD in adults",
                "Neuropsychological Testing": (
                    "Working Memory Index: 85 (Low Average)\n"
                    "Processing Speed Index: 78 (Borderline)\n"
                    "Attention/Concentration: 12th percentile\n"
                    "Sustained Attention (CPT): 68th percentile omission errors -- IMPAIRED\n"
                    "Executive Function: Moderate impairment on set-shifting and inhibition tasks"
                ),
                "Assessment": "1. ADHD, Combined Type -- confirmed  2. Executive dysfunction -- moderate  3. Comorbid depression -- address both  4. Family screening recommended -- 4-8x heritable",
            }},
        ]
    # Default generic template
    return [
        {"title": f"Medical Record -- {name}", "sections": {
            "Patient": f"Name: {name} | ID: MR-GEN",
            "Notes": "General medical documentation for testing purposes.",
        }},
    ]


# ── Family Folder Setup ─────────────────────────────────────────────────────


def setup_family_folders(pipeline: "MedRAGPipeline") -> dict[str, str]:
    """Create the 5 family member folders.

    Returns {folder_key: folder_id} mapping.
    """
    from medrag.pipeline import MedRAGPipeline

    existing_folders = {f.name: f.folder_id for f in pipeline.list_folders()}

    folder_key_to_id: dict[str, str] = {}
    seen_names: set[str] = set()

    for folder_key in FOLDER_ORDER:
        info = get_folder_info(folder_key)
        name = info["name"]
        relationship = info["relationship"]

        if name in existing_folders:
            folder_key_to_id[folder_key] = existing_folders[name]
            print(f"[medrag:download]   [OK] Folder '{name}' already exists: {existing_folders[name]}")
        elif name not in seen_names:
            folder = pipeline.create_folder(name=name, relationship=relationship)
            folder_key_to_id[folder_key] = folder.folder_id
            print(f"[medrag:download]   + Created folder '{name}' ({relationship}): {folder.folder_id}")

        seen_names.add(name)

    return folder_key_to_id


# ── Main Download Runner ────────────────────────────────────────────────────


def run_download(count: int = 50, clean: bool = False) -> dict:
    """Run the full download + ingest pipeline.

    Args:
        count: Number of documents to download/generate.
        clean: If True, delete existing folders and documents first.

    Returns:
        Dict with results: {total_ingested, per_folder, failures}
    """
    from medrag.pipeline import MedRAGPipeline

    pipeline = MedRAGPipeline()

    # Clean if requested
    if clean:
        print("[medrag:download] === Cleaning existing data ===")
        for folder in pipeline.list_folders():
            pipeline.delete_folder(folder.folder_id)
            print(f"[medrag:download]   Deleted folder: {folder.name}")
        # Also delete all documents in the default folder
        pipeline.database.delete_folder_documents("default")
        print("[medrag:download]   Cleaned default folder documents")

    # Step 1: Setup folders
    print("[medrag:download] === Setting up family folders ===")
    folder_key_to_id = setup_family_folders(pipeline)

    download_dir = Path(settings.raw_dir) / "downloads"
    per_folder_counts: dict[str, int] = {k: 0 for k in FOLDER_ORDER}
    total_ingested = 0
    failures = 0

    # Step 2: Try PMC download
    print("[medrag:download] === Fetching PMC article list ===")
    articles = download_pmc_list(download_dir)

    if articles:
        print(f"[medrag:download] Found {len(articles):,} open-access articles")

        # Step 3: Filter and assign folders
        per_folder_target = max(1, count // len(FOLDER_ORDER))
        matched = filter_medical_articles(articles, limit=count)

        if matched:
            print(f"[medrag:download] === Downloading {len(matched)} PDFs ===")

            with httpx.Client(timeout=60.0) as client:
                for i, (article, folder_key) in enumerate(matched):
                    folder_id = folder_key_to_id.get(folder_key)
                    if not folder_id:
                        continue

                    dest = download_dir / folder_key
                    pdf_path = download_pdf(article.pmcid, dest, client)

                    if pdf_path and pdf_path.exists():
                        try:
                            # Rate limit between downloads
                            if i > 0 and i % 3 == 0:
                                time.sleep(1.0)

                            pipeline.ingest_file(str(pdf_path), folder_id=folder_id)
                            per_folder_counts[folder_key] += 1
                            total_ingested += 1
                        except Exception as e:
                            print(f"[medrag:download]   [FAIL] Ingest failed for {article.pmcid}: {e}")
                            failures += 1
                    else:
                        failures += 1

    # Step 4: If PMC didn't provide enough docs, generate synthetic ones
    for folder_key in FOLDER_ORDER:
        current = per_folder_counts[folder_key]
        min_docs = max(1, count // len(FOLDER_ORDER))
        if current < min_docs:
            needed = min_docs - current
            print(f"[medrag:download] === Generating {needed} synthetic docs for {get_folder_info(folder_key)['name']} ===")
            folder_id = folder_key_to_id.get(folder_key)
            if not folder_id:
                continue

            synth_dir = download_dir / folder_key / "synthetic"
            synth_paths = generate_synthetic_docs(synth_dir, folder_key, count=needed)

            for path in synth_paths:
                try:
                    pipeline.ingest_file(str(path), folder_id=folder_id)
                    per_folder_counts[folder_key] += 1
                    total_ingested += 1
                except Exception as e:
                    print(f"[medrag:download]   [FAIL] Synthetic ingest failed: {e}")
                    failures += 1

    # Step 5: Summary
    print(f"\n[medrag:download] === Download Complete ===")
    print(f"  Total ingested: {total_ingested}")
    for folder_key in FOLDER_ORDER:
        info = get_folder_info(folder_key)
        print(f"  {info['name']}: {per_folder_counts[folder_key]} documents")
    if failures:
        print(f"  Failures: {failures}")

    return {
        "total_ingested": total_ingested,
        "per_folder": per_folder_counts,
        "failures": failures,
    }