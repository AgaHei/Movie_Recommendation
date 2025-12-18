# CineMatch Data Pipeline Overview

## 📊 Introduction

This document describes the complete data pipeline for the CineMatch movie recommendation system, from raw dataset to production-ready data structures optimized for MLOps workflows.

---

## 🎬 Dataset Information

### Source Dataset

**Name:** MovieLens 25M Dataset  
**Provider:** GroupLens Research (University of Minnesota)  
**Original Size:** 25 million movie ratings  
**URL:** https://grouplens.org/datasets/movielens/25m/

**Contents:**
- 25,000,095 ratings
- 62,423 movies
- 162,541 users
- Ratings scale: 0.5 to 5.0 stars (0.5 increments)
- Time span: 1995-2019

---

### Dataset Reduction for Academic Project

**Challenge:** Neon PostgreSQL free tier limit (512 MB)

**Solution:** Strategic sampling to fit constraints while maintaining statistical validity

#### Reduction Strategy

**Original Plan:**
```
ratings_train.parquet:  1.5 GB (70% of 25M)  ❌ Too large
ratings_test.parquet:   430 MB (20% of 25M)  ✅ Usable
ratings_buffer.parquet: 215 MB (10% of 25M)  ✅ Usable
```

**Final Implementation:**
```
ratings_initial_ml.parquet: ~250 MB (1M most recent ratings)
  ↓
Split into:
  - Training (70%): ~700k ratings
  - Testing (30%):  ~300k ratings

ratings_buffer.parquet: ~215 MB (separate subset for continuous monitoring)
  ↓
Split into 5 weekly batches:
  - batch_w1: ~500k ratings (used in simulation)
  - batch_w2: ~500k ratings
  - batch_w3: ~500k ratings (used in simulation)
  - batch_w4: ~500k ratings
  - batch_w5: ~500k ratings (used in simulation)
```

**Sampling Criteria:**
- ✅ Most recent ratings (temporal relevance)
- ✅ Maintained rating distribution
- ✅ Preserved user-movie relationship patterns
- ✅ Sufficient size for collaborative filtering

**Final Dataset Size:** ~1M ratings for training + ~130k for buffer monitoring

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: Raw Data Acquisition                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
              MovieLens 25M (CSV files)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: Local Preprocessing (Your PC)                      │
├─────────────────────────────────────────────────────────────┤
│ Tools: Python, Pandas, Jupyter Notebook                     │
│                                                              │
│ Steps:                                                       │
│ 1. Load raw CSVs (ratings.csv, movies.csv)                 │
│ 2. Exploratory Data Analysis (EDA)                         │
│ 3. Data cleaning & validation                              │
│ 4. Feature engineering (if needed)                         │
│ 5. Dataset reduction (1M sample)                           │
│ 6. Train/test split (70/30)                                │
│ 7. Buffer batch creation (5 batches)                       │
│ 8. Export to Parquet files                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: Initial Data Load to Neon                         │
├─────────────────────────────────────────────────────────────┤
│ Tool: Python script (load_academic_dataset.py)             │
│                                                              │
│ Loads:                                                       │
│ • ratings_initial_ml.parquet → ratings table               │
│   (split into train/test with data_split column)           │
│ • movie_features_small.parquet → movies table              │
│ • Creates empty ratings_buffer table (structure only)      │
│ • Creates metadata tables (ingestion, metrics, alerts)     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: Continuous Monitoring (Airflow)                    │
├─────────────────────────────────────────────────────────────┤
│ Week 1: buffer_ingestion → batch_w1 → Neon                 │
│ Week 2: buffer_ingestion → batch_w3 → Neon                 │
│ Week 3: buffer_ingestion → batch_w5 → Neon                 │
│                                                              │
│ After each ingestion: drift_monitoring analyzes changes     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: Model Training (GitHub Actions)                    │
├─────────────────────────────────────────────────────────────┤
│ Triggered when drift detected:                              │
│ • Pulls: ratings (train) + ratings_buffer (new data)       │
│ • Trains: Collaborative filtering model                     │
│ • Logs: Metrics to MLflow + model_metrics table            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

### Local Data Files

```
CineMatch/data/
├── raw/                              ← Original downloads (not in Git)
│   ├── ratings.csv                   (25M ratings)
│   ├── movies.csv                    (62k movies)
│   └── tags.csv                      (optional)
│
├── notebooks/                        ← EDA & preprocessing
│   ├── 01-eda-exploration.ipynb
│   └── 02-data-preparation.ipynb
│
├── prepared/                         ← Processed datasets
│   ├── ratings_initial_ml.parquet   (~250 MB - for training)
│   ├── ratings_buffer.parquet       (~215 MB - for monitoring)
│   ├── movie_features_small.parquet (~500 KB - with PCA)
│   └── buffer_batches/              ← Split for weekly ingestion
│       ├── batch_w1.parquet
│       ├── batch_w3.parquet
│       └── batch_w5.parquet
│
└── ingestion_scripts/                ← Load scripts
    ├── load_academic_dataset.py
    ├── split_buffer_batches.py
    └── .env                          (Neon credentials)
```

---

## 🔧 Preprocessing Steps

### Step 1: Exploratory Data Analysis (EDA)

**Notebook:** `notebooks/01-eda-exploration.ipynb`

**Analysis Performed:**
- Dataset shape and size assessment
- Missing value detection
- Rating distribution analysis
- Temporal patterns (ratings over time)
- User activity distribution
- Movie popularity distribution
- Sparsity calculation (user-movie matrix)

**Key Findings:**
```python
# Example findings from EDA
Total ratings: 25,000,095
Unique users: 162,541
Unique movies: 62,423
Rating range: 0.5 - 5.0
Average rating: 3.53
Matrix sparsity: 99.8% (very sparse)
Most rated movie: "Forrest Gump" (329k ratings)
Most active user: 123,456 (32k ratings)
```

---

### Step 2: Data Cleaning & Validation

**Notebook:** `notebooks/02-data-preparation.ipynb`

**Cleaning Operations:**

1. **Remove duplicates:**

2. **Validate rating range:**

3. **Handle timestamps:**

4. **Filter low-activity users/movies (optional):**


### Step 3: Dataset Reduction

**Goal:** Reduce from 25M to ~1M ratings while maintaining quality

**Strategy:**

```python
# Sort by timestamp (most recent first)
df_ratings = df_ratings.sort_values('timestamp', ascending=False)

# Take most recent 1M ratings
df_sampled = df_ratings.head(1_000_000)

# Verify distribution maintained
print("Original mean:", df_ratings['rating'].mean())
print("Sampled mean:", df_sampled['rating'].mean())
# Should be similar (e.g., 3.53 vs 3.54)

# Save as ratings_initial_ml.parquet
df_sampled.to_parquet('prepared/ratings_initial_ml.parquet')
```

**Validation:**
- ✅ Rating distribution preserved
- ✅ User-movie patterns maintained
- ✅ Temporal continuity (all recent data)
- ✅ Size fits Neon constraints

---

### Step 4: Train/Test Split

**Performed during Neon load** (not in preprocessing)

```python
# In load_academic_dataset.py
df_all = pd.read_parquet('ratings_initial_ml.parquet')
df_all = df_all.sort_values('timestamp')

# Split: 70% train, 30% test
train_size = int(0.7 * len(df_all))
df_train = df_all[:train_size]
df_test = df_all[train_size:]

# Add metadata
df_train['data_split'] = 'train'
df_test['data_split'] = 'test'
```

**Why split during load?**
- Keeps preprocessing simple
- Maintains temporal order (earlier ratings for training)
- Allows easy modification of split ratio

---

### Step 5: Buffer Batch Creation

**Purpose:** Simulate weekly data arrival

**Script:** `split_buffer_batches.py`

```python
import pandas as pd
from pathlib import Path

# Load full buffer data
df_buffer = pd.read_parquet('prepared/ratings_buffer.parquet')
df_buffer = df_buffer.sort_values('timestamp')

# Create batches folder
output_dir = Path('prepared/buffer_batches')
output_dir.mkdir(exist_ok=True)

# Split into 5 batches (we use 1, 3, 5 for simulation)
batch_size = len(df_buffer) // 5

for batch_num in [1, 3, 5]:  # Only create batches we'll use
    start_idx = (batch_num - 1) * batch_size
    end_idx = start_idx + batch_size
    
    batch = df_buffer.iloc[start_idx:end_idx].copy()
    batch['batch_id'] = f'batch_w{batch_num}'
    batch['ingested_at'] = None
    
    output_path = output_dir / f'batch_w{batch_num}.parquet'
    batch.to_parquet(output_path, index=False)
    print(f"✅ Created {output_path}: {len(batch):,} rows")
```

---

### Step 6: Movie Features Processing

**Input:** `movies.csv` with genres

**Processing:**

```python
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

# Load movies
df_movies = pd.read_csv('raw/movies.csv')

# Parse genres (pipe-separated)
df_movies['genres_list'] = df_movies['genres'].str.split('|')

# One-hot encode genres
mlb = MultiLabelBinarizer()
genres_encoded = mlb.fit_transform(df_movies['genres_list'])

# Create feature dataframe
df_features = pd.DataFrame(
    genres_encoded,
    columns=mlb.classes_,
    index=df_movies['movieId']
)

# Optional: PCA for dimensionality reduction
from sklearn.decomposition import PCA
pca = PCA(n_components=10)
genres_pca = pca.fit_transform(genres_encoded)

# Combine
df_movies['pca_features'] = list(genres_pca)

# Save compact version
df_movies[['movieId', 'title', 'genres', 'pca_features']].to_parquet(
    'prepared/movie_features_small.parquet'
)
```

---

## 📊 Data Statistics

### Training Dataset (ratings table)

```sql
-- In Neon after load
SELECT 
    data_split,
    COUNT(*) as num_ratings,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating,
    AVG(rating) as avg_rating,
    STDDEV(rating) as std_rating
FROM ratings
GROUP BY data_split;
```

**Expected Results:**
```
data_split | num_ratings | min_rating | max_rating | avg_rating | std_rating
-----------|-------------|------------|------------|------------|------------
train      | ~700,000    | 0.5        | 5.0        | 3.54       | 1.07
test       | ~300,000    | 0.5        | 5.0        | 3.53       | 1.06
```

### Rating Distribution

```sql
SELECT 
    rating,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM ratings
WHERE data_split = 'train'
GROUP BY rating
ORDER BY rating;
```

**Expected Distribution:**
```
rating | count    | percentage
-------|----------|------------
0.5    | 8,234    | 1.18%
1.0    | 14,562   | 2.08%
1.5    | 17,893   | 2.56%
2.0    | 42,156   | 6.02%
2.5    | 56,789   | 8.11%
3.0    | 98,234   | 14.03%
3.5    | 87,456   | 12.49%
4.0    | 178,934  | 25.56%
4.5    | 98,765   | 14.11%
5.0    | 96,977   | 13.86%
```

---

## 🗄️ Database Schema

### Core Tables

#### ratings
```sql
CREATE TABLE ratings (
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    rating FLOAT NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp BIGINT NOT NULL,
    data_split VARCHAR(10) NOT NULL,  -- 'train' or 'test'
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ratings_user ON ratings(userId);
CREATE INDEX idx_ratings_movie ON ratings(movieId);
CREATE INDEX idx_ratings_split ON ratings(data_split);
```

#### movies
```sql
CREATE TABLE movies (
    movieId INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    genres VARCHAR(200),
    pca_features JSONB  -- PCA-reduced genre embeddings
);

CREATE INDEX idx_movies_title ON movies(title);
```

#### ratings_buffer
```sql
CREATE TABLE ratings_buffer (
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    rating FLOAT NOT NULL,
    timestamp BIGINT NOT NULL,
    batch_id VARCHAR(50),        -- e.g., 'batch_w1'
    ingested_at TIMESTAMP        -- When loaded by Airflow
);

CREATE INDEX idx_buffer_batch ON ratings_buffer(batch_id);
CREATE INDEX idx_buffer_ingested ON ratings_buffer(ingested_at);
```

### Metadata Tables

#### ingestion_metadata
```sql
CREATE TABLE ingestion_metadata (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) UNIQUE NOT NULL,
    ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    status VARCHAR(20),
    notes TEXT
);
```

#### model_metrics
```sql
CREATE TABLE model_metrics (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rmse FLOAT,
    mae FLOAT,
    precision_at_10 FLOAT,
    data_size INTEGER,
    notes TEXT
);
```

#### drift_alerts
```sql
CREATE TABLE drift_alerts (
    id SERIAL PRIMARY KEY,
    alert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feature_name VARCHAR(100),
    drift_score FLOAT,
    threshold FLOAT,
    alert_triggered BOOLEAN,
    notes TEXT
);
```

---

## 🔍 Data Quality Checks

### Validation Queries

**Check for nulls:**
```sql
SELECT 
    COUNT(*) as total,
    COUNT(userId) as has_userId,
    COUNT(movieId) as has_movieId,
    COUNT(rating) as has_rating,
    COUNT(timestamp) as has_timestamp
FROM ratings;
-- All counts should be equal
```

**Verify rating range:**
```sql
SELECT 
    MIN(rating) as min_rating,
    MAX(rating) as max_rating
FROM ratings;
-- Should be: 0.5 and 5.0
```

**Check data balance:**
```sql
SELECT 
    data_split,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
FROM ratings
GROUP BY data_split;
-- Should be roughly 70/30
```

**Temporal continuity:**
```sql
SELECT 
    data_split,
    TO_TIMESTAMP(MIN(timestamp)) as earliest,
    TO_TIMESTAMP(MAX(timestamp)) as latest
FROM ratings
GROUP BY data_split;
-- Train should have earlier dates than test
```

---

## 🚀 Data Loading Process

### Initial Load Script

**Location:** `data/ingestion_scripts/load_academic_dataset.py`

**Key Functions:**

1. **Load and split ratings_initial_ml:**
```python
df_all = pd.read_parquet('prepared/ratings_initial_ml.parquet')
df_train, df_test = temporal_split(df_all, train_ratio=0.7)
```

2. **Upload to Neon:**
```python
engine = create_engine(NEON_CONNECTION_STRING)
df_train.to_sql('ratings', engine, if_exists='replace')
df_test.to_sql('ratings', engine, if_exists='append')
```

3. **Create metadata tables:**
```python
create_metadata_tables(engine)
```

**Execution:**
```bash
cd data/ingestion_scripts/
python load_academic_dataset.py
```

---

## 📈 Data Evolution Over Time

### Simulation Timeline

```
Day 0 (Initial State):
├── Neon: ratings table (1M ratings - train/test)
├── Neon: movies table (movie features)
└── Neon: ratings_buffer (EMPTY)

Day 1 (Week 1):
├── Ingest: batch_w1 → ratings_buffer (+43k)
└── Total buffer: 43k ratings

Day 2 (Week 2):
├── Ingest: batch_w3 → ratings_buffer (+43k)
└── Total buffer: 86k ratings

Day 3 (Week 3):
├── Ingest: batch_w5 → ratings_buffer (+43k)
└── Total buffer: 129k ratings
└── Drift detected! → Trigger retraining

Day 4 (Post-retraining):
├── Model trained on: ratings (1M) + ratings_buffer (129k)
├── Buffer cleared or merged
└── Ready for next monitoring cycle
```

---

## 🎯 Design Decisions & Rationale

### Why Parquet Format?

✅ **Efficient storage:** 5-10x smaller than CSV  
✅ **Fast reading:** Columnar format optimized for analytics  
✅ **Type preservation:** No need to re-specify dtypes  
✅ **Pandas native:** Easy integration with Python workflows  

### Why Temporal Splitting?

✅ **Realistic:** Train on past, test on future (no data leakage)  
✅ **Relevant:** More recent data better represents current patterns  
✅ **Valid:** Mimics production scenario (predict future from past)  

### Why Separate Buffer Data?

✅ **Clean simulation:** Buffer represents truly new production data  
✅ **No contamination:** Buffer wasn't in training/test splits  
✅ **Drift detection:** Can compare distributions independently  

### Why Only 3 Batches (1, 3, 5)?

✅ **Storage constraints:** Fit within Neon free tier  
✅ **Sufficient simulation:** Show progression over 3 weeks  
✅ **Time efficiency:** Complete simulation in 3 days  

---

## 🔗 Integration Points

### With Airflow
- Buffer batches read by `buffer_ingestion_dag`
- Metadata tracked in ingestion_metadata table

### With Training Pipeline
- Training script reads: `SELECT * FROM ratings WHERE data_split='train'`
- Can also pull buffer: `SELECT * FROM ratings_buffer`

### With Monitoring
- Drift detection compares ratings vs ratings_buffer
- Alerts logged to drift_alerts table

---

## 📚 References

**MovieLens Dataset:**
- F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19.
- https://grouplens.org/datasets/movielens/

**Data Processing Tools:**
- Pandas: https://pandas.pydata.org/
- Parquet: https://parquet.apache.org/
- SQLAlchemy: https://www.sqlalchemy.org/

---

## 📝 Maintenance Notes

### When to Re-process Data

Triggers for data pipeline re-run:
- Dataset corruption detected
- Need different sampling strategy
- Storage constraints change
- Feature engineering modifications

### Backup Strategy

**Critical files to backup:**
- `prepared/ratings_initial_ml.parquet`
- `prepared/ratings_buffer.parquet`
- `prepared/buffer_batches/*.parquet`
- `ingestion_scripts/load_academic_dataset.py`

**Storage:**
- Git LFS for large files (if needed)
- Or external storage (Google Drive, S3)

---

## 🎓 Key Takeaways

The CineMatch data pipeline demonstrates:

✅ **Strategic sampling** - Maintaining quality within constraints  
✅ **Temporal awareness** - Preserving time-based patterns  
✅ **MLOps readiness** - Data structured for continuous workflows  
✅ **Production simulation** - Realistic batch ingestion patterns  
✅ **Quality validation** - Comprehensive checks at each stage  

**Bottom Line:** A well-designed data pipeline is the foundation of reliable ML systems. Clean, validated, and well-documented data enables everything downstream—from model training to drift detection to continuous improvement.

---

**Last Updated:** December 18, 2025  
**Maintained By:** CineMatch Data Pipeline Team  
**Next Review:** After project completion
