"""
Schema/type checks for data sent to Neon via buffer ingestion.
We don't hit the database here; we only validate the pandas frame that would
be inserted, to ensure it matches the expected types.
"""

import pandas as pd


def test_buffer_payload_types(sample_batch_df):
    # Simulate the frame just before ingestion in `ingest_batch`.
    df = sample_batch_df.copy()
    df["ingested_at"] = pd.Timestamp("2025-01-01T00:00:00Z")
    df["batch_id"] = "batch_w7"

    # Expected column set
    expected_cols = {"userId", "movieId", "rating", "ingested_at", "batch_id"}
    assert set(df.columns) == expected_cols

    # Type assertions
    assert pd.api.types.is_integer_dtype(df["userId"]), "userId should be int"
    assert pd.api.types.is_integer_dtype(df["movieId"]), "movieId should be int"
    assert pd.api.types.is_float_dtype(df["rating"]), "rating should be float"
    assert pd.api.types.is_datetime64_any_dtype(df["ingested_at"]), "ingested_at should be datetime"
    assert pd.api.types.is_string_dtype(df["batch_id"]), "batch_id should be string-like"
