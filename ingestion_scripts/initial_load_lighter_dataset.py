# data/ingestion_scripts/initial_load_lighter_dataset.py
# Transfer pre-prepared data files to Neon database
# Note: Data preparation (1M row extraction, buffer batches) is done in notebook 02_Data_Preparation_MovieLens_25M.ipynb

import pandas as pd
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

NEON_CONNECTION_STRING = os.getenv("NEON_CONNECTION_STRING")
if not NEON_CONNECTION_STRING:
    raise ValueError("❌ NEON_CONNECTION_STRING not found in .env file!")

DATA_DIR = Path(__file__).parent.parent / "prepared"

# Connect to Neon
print("🔌 Connecting to Neon...")
engine = create_engine(NEON_CONNECTION_STRING)

# ========== LOAD ratings_initial_ml.parquet (1M most recent rows, for train + test) ==========
print("\n📊 Loading ratings_initial_ml.parquet...")
df_ratings = pd.read_parquet(DATA_DIR / "ratings_initial_ml.parquet")
print(f"   Total shape: {df_ratings.shape}")
print(f"   Columns: {df_ratings.columns.tolist()}")

# Sort by timestamp to maintain temporal order
df_ratings = df_ratings.sort_values('timestamp')

# Split: 70% train, 30% test (or 80/20 if you prefer)
train_size = int(0.7 * len(df_ratings))

df_train = df_ratings[:train_size].copy()
df_test = df_ratings[train_size:].copy()

print(f"\n📈 Split from ratings_initial_ml.parquet:")
print(f"   Train: {len(df_train):,} rows ({len(df_train)/len(df_ratings)*100:.1f}%)")
print(f"   Test: {len(df_test):,} rows ({len(df_test)/len(df_ratings)*100:.1f}%)")

# Add metadata columns
df_train['data_split'] = 'train'
df_train['loaded_at'] = pd.Timestamp.now()

df_test['data_split'] = 'test'
df_test['loaded_at'] = pd.Timestamp.now()

# ========== UPLOAD TRAINING DATA ==========
print("\n⬆️  Uploading training data to Neon...")
df_train.to_sql(
    'ratings', 
    engine, 
    if_exists='replace',  # Create new table
    index=False, 
    method=None,  # Use simple inserts to avoid parameter limits
    chunksize=10000
)
print("   ✅ Training data loaded!")

# ========== UPLOAD TEST DATA ==========
print("\n⬆️  Uploading test data to Neon...")
df_test.to_sql(
    'ratings', 
    engine, 
    if_exists='append',  # Append to training data in same table
    index=False, 
    method=None,  # Use simple inserts
    chunksize=10000
)
print("   ✅ Test data loaded!")

# Note: First run uses 'replace' for training data, then 'append' for test.
# If you need to re-run this script, it will duplicate test data.
# For clean re-runs, training data 'replace' will clear the table first.

# ========== CREATE EMPTY BUFFER TABLE STRUCTURE ==========
print("\n📦 Loading ratings_buffer.parquet for schema...")
df_buffer = pd.read_parquet(DATA_DIR / "ratings_buffer.parquet")
print(f"   Buffer shape: {df_buffer.shape}")

# Create empty buffer table structure in Neon
# Note: Buffer batches are pre-created in notebook (buffer_batches/batch_w{1-5}.parquet)
print("\n⬆️  Creating ratings_buffer table structure in Neon...")
df_buffer_schema = df_buffer.copy()
df_buffer_schema['batch_id'] = None
df_buffer_schema['ingested_at'] = None
df_buffer_schema.head(0).to_sql('ratings_buffer', engine, if_exists='replace', index=False)
print("   ✅ Buffer table structure created (empty, ready for Airflow)")

# ========== LOAD MOVIE FEATURES ==========
print("\n🎬 Loading movie_features_small.parquet...")
df_movies = pd.read_parquet(DATA_DIR / "movie_features_small.parquet")
print(f"   Shape: {df_movies.shape}")
print(f"   Columns: {df_movies.columns.tolist()}")

print("   Uploading to Neon...")
df_movies.to_sql(
    'movies', 
    engine, 
    if_exists='replace', 
    index=False, 
    method='multi', 
    chunksize=5000
)
print("   ✅ Movie features loaded!")

# ========== CREATE METADATA TABLES ==========
print("\n🗂️  Creating metadata tables...")

# Ingestion metadata
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingestion_metadata (
            id SERIAL PRIMARY KEY,
            batch_id VARCHAR(50) UNIQUE NOT NULL,
            ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_count INTEGER,
            status VARCHAR(20),
            notes TEXT
        );
    """))
    conn.commit()
print("   ✅ ingestion_metadata table created")

# Model metrics
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS model_metrics (
            id SERIAL PRIMARY KEY,
            model_version VARCHAR(50) NOT NULL,
            training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rmse FLOAT,
            mae FLOAT,
            precision_at_10 FLOAT,
            data_size INTEGER,
            notes TEXT
        );
    """))
    conn.commit()
print("   ✅ model_metrics table created")

# Drift alerts
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS drift_alerts (
            id SERIAL PRIMARY KEY,
            alert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            feature_name VARCHAR(100),
            drift_score FLOAT,
            threshold FLOAT,
            alert_triggered BOOLEAN,
            notes TEXT
        );
    """))
    conn.commit()
print("   ✅ drift_alerts table created")

# ========== SUMMARY ==========
print("\n" + "="*70)
print("🎉 CINEMATCH DATA LOAD COMPLETE!")
print("="*70)
print("\n📊 DATA IN NEON:")
print(f"   ✅ ratings table: {len(df_train) + len(df_test):,} rows")
print(f"      - Train split: {len(df_train):,} rows (from ratings_initial_ml.parquet)")
print(f"      - Test split: {len(df_test):,} rows (from ratings_initial_ml.parquet)")
print(f"   ✅ movies table: {len(df_movies):,} rows")
print(f"   ✅ ratings_buffer table: Structure ready (empty)")
print(f"   ✅ ingestion_metadata table: Ready")
print(f"   ✅ model_metrics table: Ready")
print(f"   ✅ drift_alerts table: Ready")

print("\n💾 BUFFER BATCHES (Pre-prepared in notebook):")
print(f"   ✅ 5 weekly batches ready in: prepared/buffer_batches/")
print(f"   ✅ Buffer table structure created in Neon (empty, ready for Airflow ingestion)")

print("\n🎯 DATA SOURCE SUMMARY:")
print(f"   • ratings_initial_ml.parquet → Train + Test in Neon (1M rows)")
print(f"   • ratings_buffer.parquet → 5 weekly batches (local files)")
print(f"   • movie_features_small.parquet → Movies table in Neon")

print("\n🚀 Your Neon database is ready for the MLOps pipeline!")
print("="*70)
