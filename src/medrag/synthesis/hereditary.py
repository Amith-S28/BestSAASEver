"""Hereditary conditions fallback — hardcoded reference for zero-cache scenarios.

This file provides a fallback hereditary conditions list used when the
MedGen/HPO/GeneReviews cache is not yet synced or is corrupted. All language
has been reframed per FDA guidance: risk figures are population-level
education, not patient-specific predictions.

For the real data pipeline, see:
  - hereditary_cache.py  — cache management
  - hereditary_sync.py   — MedGen/HPO/GeneReviews sync
  - hereditary_matcher.py — query-time relevance filtering

Run `medrag sync-hereditary` to populate the cache with real medical data.
"""

from __future__ import annotations

import numpy as np

# Fallback conditions with FDA-compliant educational risk language.
# Replaces the old HEREDITARY_CONDITIONS — data here is from general medical
# knowledge (AI training data), NOT from a validated medical database.
# The real pipeline fetches from NIH MedGen, HPO, and GeneReviews.

FALLBACK_CONDITIONS = [
    # ── Metabolic / Endocrine ──────────────────────────────────────────
    {
        "condition": "Type 2 Diabetes",
        "inheritance": "multifactorial (strong family clustering)",
        "markers": ["HbA1c", "fasting glucose", "insulin resistance", "prediabetes", "A1C"],
        "inheritance_description": "This condition has multifactorial inheritance — risk is influenced by multiple genetic and environmental factors.",
        "risk_note_educational": "Population studies show first-degree relatives have a 2-6x increased relative risk compared to the general population. If both parents are affected, population-level risk estimates approach ~50%.",
    },
    {
        "condition": "Type 1 Diabetes",
        "inheritance": "autoimmune (HLA-linked)",
        "markers": ["autoantibodies", "GAD65", "IA-2", "insulin antibodies", "C-peptide low"],
        "inheritance_description": "This condition has an autoimmune inheritance pattern linked to HLA genes.",
        "risk_note_educational": "Population studies show ~5-10% prevalence in first-degree relatives vs ~0.4% in the general population.",
    },
    {
        "condition": "Hyperlipidemia / Familial Hypercholesterolemia",
        "inheritance": "autosomal dominant (LDLR, APOB, PCSK9)",
        "markers": ["LDL > 190", "total cholesterol > 300", "xanthomas", "tendon xanthomas", "LDL-C"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Population prevalence is ~1 in 250. Untreated, individuals have approximately 20x increased relative coronary risk.",
    },
    {
        "condition": "Thyroid Disorders (Hashimoto's / Graves')",
        "inheritance": "autoimmune (multifactorial)",
        "markers": ["TSH", "TPO antibodies", "TgAb", "TSI", "free T4", "hyperthyroid", "hypothyroid"],
        "inheritance_description": "This condition has multifactorial autoimmune inheritance.",
        "risk_note_educational": "Strong familial aggregation observed in population studies. Relatives of individuals with one autoimmune thyroid condition have higher prevalence of any autoimmune thyroid condition.",
    },

    # ── Cardiovascular ─────────────────────────────────────────────────
    {
        "condition": "Hypertension",
        "inheritance": "multifactorial (30-50% heritable)",
        "markers": ["blood pressure", "systolic", "diastolic", "BP readings", "antihypertensive"],
        "inheritance_description": "This condition has multifactorial inheritance with 30-50% heritability estimates from twin studies.",
        "risk_note_educational": "Population studies show first-degree relatives have a 2-4x increased relative risk. Early-onset (<55M/<65F) suggests a stronger genetic component.",
    },
    {
        "condition": "Coronary Artery Disease",
        "inheritance": "multifactorial (40-60% heritable)",
        "markers": ["coronary", "atherosclerosis", "stent", "bypass", "CABG", "angioplasty", "troponin", "CAD"],
        "inheritance_description": "This condition has multifactorial inheritance with 40-60% heritability estimates.",
        "risk_note_educational": "Population studies show premature CAD in a first-degree relative (<55M/<65F) approximately doubles relative risk.",
    },
    {
        "condition": "Cardiomyopathy (Hypertrophic)",
        "inheritance": "autosomal dominant (MYH7, MYBPC3)",
        "markers": ["wall thickness > 15mm", "septal hypertrophy", "LVH", "SAM", "outflow obstruction"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Clinical guidelines recommend echocardiogram screening for first-degree relatives.",
    },
    {
        "condition": "Long QT Syndrome",
        "inheritance": "autosomal dominant (KCNQ1, KCNH2, SCN5A)",
        "markers": ["QTc > 460ms", "prolonged QT", "syncope", "sudden cardiac"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Clinical guidelines recommend ECG screening for first-degree relatives.",
    },
    {
        "condition": "Atrial Fibrillation",
        "inheritance": "multifactorial (genetic predisposition)",
        "markers": ["AFib", "atrial fibrillation", "irregular rhythm", "anticoagulation"],
        "inheritance_description": "This condition has multifactorial inheritance with a genetic predisposition component.",
        "risk_note_educational": "Population studies show first-degree relatives have approximately 40% increased relative risk. Early-onset AFib has a stronger genetic link.",
    },

    # ── Oncology ──────────────────────────────────────────────────────
    {
        "condition": "BRCA1/BRCA2 Breast & Ovarian Cancer",
        "inheritance": "autosomal dominant",
        "markers": ["BRCA", "breast cancer <50", "triple-negative", "ovarian cancer", "male breast cancer", "bilateral breast cancer"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Population studies: BRCA1 carriers have 55-72% lifetime breast cancer probability and 39-44% ovarian cancer probability by age 70-80. BRCA2 carriers: 45-69% breast, 11-17% ovarian.",
    },
    {
        "condition": "Lynch Syndrome (HNPCC)",
        "inheritance": "autosomal dominant (MLH1, MSH2, MSH6, PMS2)",
        "markers": ["colorectal cancer <50", "endometrial cancer", "MLH1", "MSH2", "MSI-high", "microsatellite instability"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Population studies show 40-80% lifetime colorectal cancer probability in carriers. Clinical guidelines recommend colonoscopy screening starting at age 20-25.",
    },
    {
        "condition": "FAP (Familial Adenomatous Polyposis)",
        "inheritance": "autosomal dominant (APC gene)",
        "markers": ["polyps > 100", "adenomatous polyps", "APC mutation", "colon polyps young age"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Population studies show nearly 100% colorectal cancer probability by age 40-50 without colectomy in carriers.",
    },
    {
        "condition": "Prostate Cancer (hereditary)",
        "inheritance": "multifactorial (BRCA2, HOXB13)",
        "markers": ["PSA", "prostate cancer <55", "Gleason >7", "BRCA2"],
        "inheritance_description": "This condition has multifactorial inheritance with identified genetic risk variants.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-3x increased relative risk. Multiple affected relatives: 5-10x relative risk.",
    },
    {
        "condition": "Melanoma",
        "inheritance": "multifactorial (CDKN2A, CDK4)",
        "markers": ["melanoma", "dysplastic nevi", "CDKN2A", "atypical moles", "FAMMM"],
        "inheritance_description": "This condition has multifactorial inheritance with identified genetic risk variants.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-8x increased relative risk. CDKN2A carriers: 28-76% estimated lifetime probability.",
    },

    # ── Neurological ───────────────────────────────────────────────────
    {
        "condition": "Alzheimer's Disease",
        "inheritance": "multifactorial (APOE4 increases risk 3-12x)",
        "markers": ["dementia", "cognitive decline", "APOE4", "memory loss", "early-onset dementia <65"],
        "inheritance_description": "This condition has multifactorial inheritance. APOE4 allele increases relative risk 3-12x in population studies.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-4x increased relative risk. APOE4 homozygous individuals have approximately 12x relative risk.",
    },
    {
        "condition": "Parkinson's Disease",
        "inheritance": "multifactorial (LRRK2, SNCA, GBA)",
        "markers": ["Parkinson", "tremor", "bradykinesia", "LRRK2", "GBA mutation"],
        "inheritance_description": "This condition has multifactorial inheritance with identified genetic risk variants.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-3x increased relative risk. LRRK2 carriers: estimated 28-74% penetrance by age 80.",
    },
    {
        "condition": "Huntington's Disease",
        "inheritance": "autosomal dominant (CAG repeat in HTT)",
        "markers": ["Huntington", "chorea", "CAG repeat >36", "HTT", "involuntary movements"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Genetic testing is definitive for this condition.",
    },
    {
        "condition": "Epilepsy",
        "inheritance": "multifactorial (various channelopathy genes)",
        "markers": ["seizure", "epilepsy", "EEG abnormal", "convulsion"],
        "inheritance_description": "This condition has multifactorial inheritance. Specific epilepsy syndromes (e.g., juvenile myoclonic) have a stronger genetic component.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-4x increased relative risk.",
    },

    # ── Hematologic ────────────────────────────────────────────────────
    {
        "condition": "Sickle Cell Disease / Trait",
        "inheritance": "autosomal recessive (HBB)",
        "markers": ["sickle cell", "HbS", "hemoglobin S", "sickle", "SCD", "pain crisis"],
        "inheritance_description": "In autosomal recessive inheritance, when both parents are carriers, each child has a 25% probability of being affected, 50% probability of being a carrier, and 25% probability of being unaffected.",
        "risk_note_educational": "Higher prevalence in populations of African, Mediterranean, and Middle Eastern descent.",
    },
    {
        "condition": "Thalassemia",
        "inheritance": "autosomal recessive (HBA1/HBA2 for alpha, HBB for beta)",
        "markers": ["thalassemia", "microcytic anemia", "HbA2 elevated", "MCV low", "iron studies normal", "alpha thalassemia", "beta thalassemia"],
        "inheritance_description": "In autosomal recessive inheritance, when both parents are carriers, each child has a 25% probability of being affected with severe disease.",
        "risk_note_educational": "Clinical guidelines recommend screening with CBC + Hb electrophoresis.",
    },
    {
        "condition": "Factor V Leiden / Thrombophilia",
        "inheritance": "autosomal dominant (F5, F2 prothrombin)",
        "markers": ["DVT", "PE", "pulmonary embolism", "thrombosis", "Factor V Leiden", "prothrombin mutation", "blood clot"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "Population studies show heterozygous carriers have 3-8x increased relative DVT risk. Homozygous: 50-100x relative risk.",
    },
    {
        "condition": "Hemochromatosis",
        "inheritance": "autosomal recessive (HFE C282Y, H63D)",
        "markers": ["ferritin", "iron overload", "transferrin saturation >45%", "C282Y", "HFE", "liver iron", "hemochromatosis"],
        "inheritance_description": "In autosomal recessive inheritance, when both parents are carriers, each child has a 25% probability of being homozygous.",
        "risk_note_educational": "Population studies show C282Y homozygotes have 28-44% estimated penetrance for clinical disease. Siblings of an affected individual have a 25% probability of being homozygous.",
    },

    # ── Autoimmune ────────────────────────────────────────────────────
    {
        "condition": "Celiac Disease",
        "inheritance": "multifactorial (HLA-DQ2/DQ8 required)",
        "markers": ["tTG-IgA", "EMA", "celiac", "gluten", "duodenal biopsy", "villous atrophy", "DQ2", "DQ8"],
        "inheritance_description": "This condition requires HLA-DQ2 or DQ8 for susceptibility, but not all carriers develop the condition.",
        "risk_note_educational": "Population studies show 10-15% prevalence in first-degree relatives vs ~1% in the general population.",
    },
    {
        "condition": "Inflammatory Bowel Disease (Crohn's / UC)",
        "inheritance": "multifactorial (NOD2, IL23R, ATG16L1)",
        "markers": ["Crohn", "ulcerative colitis", "IBD", "CRP elevated", "fecal calprotectin", "colonoscopy inflammation"],
        "inheritance_description": "This condition has multifactorial inheritance with identified genetic risk variants.",
        "risk_note_educational": "Population studies show first-degree relatives have 5-10x increased relative risk.",
    },
    {
        "condition": "Rheumatoid Arthritis",
        "inheritance": "multifactorial (HLA-DRB1 shared epitope)",
        "markers": ["RA", "rheumatoid factor", "anti-CCP", "RF positive", "joint erosion", "morning stiffness >1hr"],
        "inheritance_description": "This condition has multifactorial inheritance with HLA-DRB1 shared epitope as a major genetic risk factor.",
        "risk_note_educational": "Population studies show first-degree relatives have 3-5x increased relative risk.",
    },
    {
        "condition": "Lupus (SLE)",
        "inheritance": "multifactorial (HLA, complement deficiencies)",
        "markers": ["ANA", "anti-dsDNA", "SLE", "lupus", "complement C3/C4 low", "anti-Smith"],
        "inheritance_description": "This condition has multifactorial inheritance involving HLA and complement deficiency genes.",
        "risk_note_educational": "Population studies show first-degree relatives have 5-8x increased relative risk in females. Concordance rate in identical twin studies: ~25%.",
    },
    {
        "condition": "Multiple Sclerosis",
        "inheritance": "multifactorial (HLA-DRB1*15:01)",
        "markers": ["MS", "multiple sclerosis", "MRI lesions", "oligoclonal bands", "demyelination"],
        "inheritance_description": "This condition has multifactorial inheritance with HLA-DRB1*15:01 as the strongest known genetic risk factor.",
        "risk_note_educational": "Population studies show first-degree relatives have 20-40x increased relative risk vs general population (~0.1% to ~2-4%).",
    },

    # ── Renal ──────────────────────────────────────────────────────────
    {
        "condition": "Polycystic Kidney Disease (ADPKD)",
        "inheritance": "autosomal dominant (PKD1, PKD2)",
        "markers": ["kidney cysts", "PKD", "polycystic", "renal cysts", "kidney enlargement", "creatinine rising"],
        "inheritance_description": "In autosomal dominant inheritance, each child of an affected individual has a 50% probability of inheriting the pathogenic variant.",
        "risk_note_educational": "PKD1 is typically more severe (ESRD by ~55yo). Clinical guidelines recommend renal ultrasound screening.",
    },

    # ── Respiratory ────────────────────────────────────────────────────
    {
        "condition": "Alpha-1 Antitrypsin Deficiency",
        "inheritance": "autosomal recessive (SERPINA1)",
        "markers": ["A1AT", "alpha-1", "PiZ", "PiS", "emphysema young", "liver disease", "panacinar emphysema"],
        "inheritance_description": "In autosomal recessive inheritance, when both parents are carriers, each child has a 25% probability of being affected.",
        "risk_note_educational": "ZZ genotype results in severe deficiency. MZ carriers have moderate risk. Testing recommended if early-onset COPD or unexplained liver disease is present in the family.",
    },
    {
        "condition": "Cystic Fibrosis",
        "inheritance": "autosomal recessive (CFTR)",
        "markers": ["CFTR", "cystic fibrosis", "sweat chloride", "pancreatic insufficiency", "recurrent pneumonia"],
        "inheritance_description": "In autosomal recessive inheritance, when both parents are carriers, each child has a 25% probability of being affected.",
        "risk_note_educational": "Approximately 1 in 25 individuals of Caucasian descent are carriers. Newborn screening is standard in many regions.",
    },

    # ── Mental Health ──────────────────────────────────────────────────
    {
        "condition": "Major Depression",
        "inheritance": "multifactorial (~40% heritable)",
        "markers": ["depression", "MDD", "antidepressant", "SSRI", "SNRI", "suicidal ideation"],
        "inheritance_description": "This condition has multifactorial inheritance with ~40% heritability estimates from twin studies.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-3x increased relative risk. Early-onset and recurrent forms have higher heritability.",
    },
    {
        "condition": "Bipolar Disorder",
        "inheritance": "multifactorial (~60-85% heritable)",
        "markers": ["bipolar", "mania", "hypomania", "mood stabilizer", "lithium", "lamotrigine"],
        "inheritance_description": "This condition has multifactorial inheritance with ~60-85% heritability estimates — among the highest for psychiatric conditions.",
        "risk_note_educational": "Population studies show first-degree relatives have 5-10x increased relative risk.",
    },
    {
        "condition": "Schizophrenia",
        "inheritance": "multifactorial (~80% heritable)",
        "markers": ["schizophrenia", "psychosis", "hallucinations", "antipsychotic", "thought disorder"],
        "inheritance_description": "This condition has multifactorial inheritance with ~80% heritability estimates from twin studies.",
        "risk_note_educational": "Population studies show first-degree relatives have approximately 10x increased relative risk (~10% vs ~1% general population).",
    },
    {
        "condition": "ADHD",
        "inheritance": "multifactorial (~70-80% heritable)",
        "markers": ["ADHD", "attention deficit", "stimulant", "methylphenidate", "amphetamine", "executive dysfunction"],
        "inheritance_description": "This condition has multifactorial inheritance with ~70-80% heritability estimates — among the highest for psychiatric conditions.",
        "risk_note_educational": "Population studies show first-degree relatives have 4-8x increased relative risk.",
    },

    # ── Ophthalmologic ─────────────────────────────────────────────────
    {
        "condition": "Glaucoma",
        "inheritance": "multifactorial (MYOC, OPTN for early-onset)",
        "markers": ["intraocular pressure", "IOP", "glaucoma", "cup-to-disc ratio", "visual field loss", "optic nerve"],
        "inheritance_description": "This condition has multifactorial inheritance. Early-onset forms may involve MYOC or OPTN genes.",
        "risk_note_educational": "Population studies show first-degree relatives have 4-9x increased relative risk. Clinical guidelines recommend screening relatives >40yo.",
    },
    {
        "condition": "Macular Degeneration (AMD)",
        "inheritance": "multifactorial (CFH, ARMS2)",
        "markers": ["macular degeneration", "AMD", "drusen", "AREDS", "choroidal neovascularization"],
        "inheritance_description": "This condition has multifactorial inheritance with CFH and ARMS2 as major genetic risk factors.",
        "risk_note_educational": "Population studies show first-degree relatives have 2-4x increased relative risk. Smoking combined with genetic factors multiplies risk.",
    },
]


def build_hereditary_reference(
    query_vector: np.ndarray | None = None,
    query_text: str = "",
) -> str:
    """Build a hereditary conditions reference for the LLM prompt.

    Delegates to the matcher (which uses cached MedGen/HPO data if available)
    or falls back to the hardcoded FALLBACK_CONDITIONS list.

    Args:
        query_vector: Precomputed query embedding for relevance matching.
        query_text: Original query text (used as fallback signal).

    Returns:
        Formatted reference string with disclaimers and source attribution.
    """
    from medrag.synthesis.hereditary_matcher import build_relevant_reference
    return build_relevant_reference(query_vector, query_text)


# Number of tokens in the fallback reference (approximate)
if __name__ == "__main__":
    from medrag.synthesis.hereditary_matcher import build_fallback_reference
    ref = build_fallback_reference()
    print(f"Fallback reference: {len(ref)} chars, ~{len(ref.split())} words")
    print()
    print(ref[:500] + "...")