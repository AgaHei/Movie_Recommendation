import pandas as pd
from pathlib import Path

# Load full ratings
DATA_DIR = Path('prepared')
df = pd.read_parquet(DATA_DIR / 'ratings_test.parquet')
print(f'Full dataset: {len(df):,} rows')

# Take 1M most recent by timestamp
df_sorted = df.sort_values('timestamp', ascending=False)
df_sample = df_sorted.head(1000000).reset_index(drop=True)
print(f'Sample (1M most recent): {len(df_sample):,} rows')
print(f'Timestamp range: {df_sample["timestamp"].min()} to {df_sample["timestamp"].max()}')

# Save to new file
output_path = DATA_DIR / 'ratings_initial_ml.parquet'
df_sample.to_parquet(output_path, index=False)
print(f'Saved to: {output_path}')
