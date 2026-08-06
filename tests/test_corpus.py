"""Tests for the Hugging Face MedRAG Corpus ingestor."""

import pytest
from unittest.mock import MagicMock, patch

from medrag.corpus import CorpusIngestor

@pytest.fixture
def mock_dataset():
    """Returns a mock streaming dataset iterator."""
    return [
        {
            "id": "textbook_1",
            "title": "Harrison's Principles of Internal Medicine",
            "content": "Hypertension is a chronic medical condition in which the blood pressure in the arteries is persistently elevated.",
            "contents": "Harrison's Principles of Internal Medicine\nHypertension is a chronic medical condition..."
        },
        {
            "id": "textbook_2",
            "title": "Robbins Basic Pathology",
            "content": "Inflammation is a complex biological response of vascular tissues to harmful stimuli.",
            "contents": "Robbins Basic Pathology\nInflammation is a complex biological response..."
        }
    ]

@patch("medrag.corpus.load_dataset")
def test_corpus_ingestion(mock_load_dataset, mock_dataset):
    """Test that the corpus ingestor correctly parses and batches HF dataset items."""
    mock_load_dataset.return_value = mock_dataset
    
    # Mock the pipeline so we don't do real embedding/indexing
    mock_pipeline = MagicMock()
    mock_folder = MagicMock()
    mock_folder.folder_id = "corpus_textbooks"
    mock_pipeline.get_folder.return_value = None
    mock_pipeline.create_folder.return_value = mock_folder
    
    # We want to inspect what was indexed
    indexed_docs = []
    def fake_index(docs, vectors, folder_id):
        indexed_docs.extend(docs)
        
    mock_pipeline.database.index_documents.side_effect = fake_index
    
    # Run ingestion with a small batch size to force it
    ingestor = CorpusIngestor(pipeline=mock_pipeline)
    ingestor.ingest_subset("textbooks", limit=10, batch_size=1)
    
    # Verifications
    mock_load_dataset.assert_called_once_with("MedRAG/textbooks", split="train", streaming=True, cache_dir="data/raw/downloads/Corpus")
    mock_pipeline.create_folder.assert_called_once()
    
    assert len(indexed_docs) == 2
    
    doc1 = indexed_docs[0]
    assert doc1.doc_id == "hf_textbook_1"
    assert "Hypertension" in doc1.markdown
    assert "Harrison's" in doc1.markdown
    
    doc2 = indexed_docs[1]
    assert doc2.doc_id == "hf_textbook_2"
    assert "Inflammation" in doc2.markdown
    assert "Robbins" in doc2.markdown
