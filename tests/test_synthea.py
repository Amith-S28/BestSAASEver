from pathlib import Path
from unittest.mock import MagicMock, patch

from medrag.synthea import SyntheaIngestor

def test_synthea_ingestor_csv_parsing(tmp_path):
    """Test the Synthea ingestor reads CSVs correctly."""
    
    # Create fake CSV data in a temp directory
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    
    (csv_dir / "patients.csv").write_text("Id,BIRTHDATE,DEATHDATE,SSN,DRIVERS,PASSPORT,PREFIX,FIRST,LAST,SUFFIX,MAIDEN,MARITAL,RACE,ETHNICITY,GENDER,BIRTHPLACE,ADDRESS,CITY,STATE,COUNTY,ZIP,LAT,LON,HEALTHCARE_EXPENSES,HEALTHCARE_COVERAGE\n"
                                          "patient_1,1980-01-01,,,,,Mr.,Test,Patient,,,,,,M,,,,,,,,,,", encoding="utf-8")
    
    (csv_dir / "encounters.csv").write_text("Id,START,STOP,PATIENT,ORGANIZATION,PROVIDER,PAYER,ENCOUNTERCLASS,CODE,DESCRIPTION,BASE_ENCOUNTER_COST,TOTAL_CLAIM_COST,PAYER_COVERAGE,REASONCODE,REASONDESCRIPTION\n"
                                            "enc_1,2023-01-01T00:00:00Z,,patient_1,,,,,ambulatory,,General Examination,,,,", encoding="utf-8")
    
    (csv_dir / "conditions.csv").write_text("START,STOP,PATIENT,ENCOUNTER,CODE,DESCRIPTION\n"
                                            "2023-01-01,,patient_1,enc_1,1234,Hypertension", encoding="utf-8")
                                            
    (csv_dir / "medications.csv").write_text("START,STOP,PATIENT,PAYER,ENCOUNTER,CODE,DESCRIPTION,BASE_COST,PAYER_COVERAGE,DISPENSES,TOTALCOST,REASONCODE,REASONDESCRIPTION\n"
                                             "2023-01-01,,patient_1,,enc_1,,Lisinopril,,,,,,,", encoding="utf-8")
                                             
    (csv_dir / "observations.csv").write_text("DATE,PATIENT,ENCOUNTER,CATEGORY,CODE,DESCRIPTION,VALUE,UNITS,TYPE\n"
                                              "2023-01-01,patient_1,enc_1,vital-signs,,Blood Pressure,130/80,mmHg,text", encoding="utf-8")

    out_dir = tmp_path / "SyntheticData"
    ingestor = SyntheaIngestor(output_dir=str(out_dir))
    
    # Mock MedRAGPipeline so we don't actually hit LanceDB in the unit test
    mock_pipeline = MagicMock()
    mock_folder = MagicMock()
    mock_folder.folder_id = "test_folder_1"
    mock_pipeline.create_folder.return_value = mock_folder
    ingestor.pipeline = mock_pipeline
    
    # Process the fake CSVs
    ingestor.process(csv_dir=str(csv_dir), limit_patients=1)
    
    # Verify outputs
    patient_dir = out_dir / "Test_Patient"
    assert patient_dir.exists(), "Patient output directory should be created"
    
    # Check if a PDF was generated for the encounter
    # Date is extracted from '2023-01-01T00:00:00Z' -> '2023-01-01'
    expected_pdf = patient_dir / "2023-01-01_ambulatory.pdf"
    assert expected_pdf.exists(), f"PDF should be generated at {expected_pdf}"
    
    # Verify that pipeline was called to ingest the file
    mock_pipeline.ingest_file.assert_called_once_with(str(expected_pdf), folder_id="test_folder_1")
    mock_pipeline.create_folder.assert_called_once_with(name="Test Patient", notes="Synthea generated. DOB: 1980-01-01")
