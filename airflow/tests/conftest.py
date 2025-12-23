"""
Sample MovieLens-like batch for testing.
This fixture provides a small MovieLens-like DataFrame used across multiple tests.
It ensures consistent, controlled input data for testing ingestion, transformation, and validation logic without relying on external files or databases.

"""

import pytest
import pandas as pd

@pytest.fixture
def sample_batch_df():

    return pd.DataFrame({
        "userId": [1, 2, 3],
        "movieId": [10, 20, 30],
        "rating": [4.0, 5.0, 3.5],
    })
