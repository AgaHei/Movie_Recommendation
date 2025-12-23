"""
Basic unit tests for ingestion logic.
"""

import pytest
from dags.buffer_ingestion_dag import ingest_batch

def test_ingest_fails_without_neon_env(monkeypatch):
    monkeypatch.delenv("NEON_CONNECTION_STRING", raising=False)

    with pytest.raises(ValueError):
        ingest_batch(batch_number=7)
