# CineMatch Neon Database Schema

## 🗄️ Overview

This document provides a complete reference for the CineMatch database schema hosted on Neon PostgreSQL. The schema is designed to support a production-grade MLOps pipeline with data ingestion, model training, drift monitoring, and continuous improvement.

---

## 📊 Database Information

**Platform:** Neon PostgreSQL (Serverless Postgres)  
**Database Name:** `cinematch_db` (or your Neon default database)  
**PostgreSQL Version:** 15  
**Storage Tier:** Free tier (512 MB limit)  
**Region:** eu-central-1 (Frankfurt)

**Connection Details:**
```
Host: ep-xxxxx.eu-central-1.aws.neon.tech
Port: 5432
Database: neondb
SSL Mode: Required
```

---

## 🏗️ Schema Architecture

### Database Design Principles

The schema follows these design patterns:

1. **Separation of Concerns**
   - Core data tables (ratings, movies)
   - Buffer/staging tables (ratings_buffer)
   - Operational metadata (ingestion_metadata, model_metrics, drift_alerts)

2. **Temporal Design**
   - All tables include timestamps for audit trails
   - Training data separated by `data_split` flag
   - Buffer data tracked by `batch_id`

3. **OLAP Optimization**
   - Denormalized for analytical queries
   - Indexes on frequently queried columns
   - Optimized for batch reads over transactional writes

4. **MLOps Integration**
   - Metadata tables support continuous monitoring
   - Drift detection logged for decision-making
   - Model performance tracked over time

---

## 📋 Table Catalog

### Core Data Tables

| Table | Purpose | Records | Size |
|-------|---------|---------|------|
| `ratings` | Training & test data | ~1M | ~250 MB |
| `movies` | Movie metadata & features | ~60k | ~5 MB |
| `ratings_buffer` | Continuous monitoring data | 0-130k | 0-30 MB |

### Metadata Tables

| Table | Purpose | Records | Size |
|-------|---------|---------|------|
| `ingestion_metadata` | Batch ingestion logs | ~10 | <1 MB |
| `model_metrics` | Model performance history | ~10 | <1 MB |
| `drift_alerts` | Drift detection results | ~30 | <1 MB |

---

## 📊 Core Data Tables

### Table: `ratings`

**Purpose:** Main training and test dataset for collaborative filtering

**Description:** Contains historical movie ratings used for initial model training and validation. Split into training (70%) and test (30%) subsets using the `data_split` column.

#### Schema

```sql
CREATE TABLE ratings (
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    rating FLOAT NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp BIGINT NOT NULL,
    data_split VARCHAR(10) NOT NULL CHECK (data_split IN ('train', 'test')),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `userId` | INTEGER | NOT NULL | User identifier from MovieLens dataset |
| `movieId` | INTEGER | NOT NULL | Movie identifier from MovieLens dataset |
| `rating` | FLOAT | NOT NULL, 0.5-5.0 | Star rating (0.5 increments) |
| `timestamp` | BIGINT | NOT NULL | Unix timestamp when rating was created |
| `data_split` | VARCHAR(10) | NOT NULL, 'train'/'test' | Dataset split for training vs validation |
| `loaded_at` | TIMESTAMP | DEFAULT NOW | When record was loaded into Neon |

#### Indexes

```sql
CREATE INDEX idx_ratings_user ON ratings(userId);
CREATE INDEX idx_ratings_movie ON ratings(movieId);
CREATE INDEX idx_ratings_split ON ratings(data_split);
CREATE INDEX idx_ratings_timestamp ON ratings(timestamp);
```

**Index Rationale:**
- `userId`: Fast user-based filtering for collaborative filtering
- `movieId`: Fast movie-based aggregations
- `data_split`: Separate train/test queries efficiently
- `timestamp`: Temporal analysis and sorting

#### Sample Data

```sql
SELECT * FROM ratings LIMIT 5;
```

```
userId | movieId | rating | timestamp  | data_split | loaded_at
-------|---------|--------|------------|------------|-------------------
1      | 122     | 5.0    | 1112486027 | train      | 2025-12-17 08:30:15
1      | 185     | 4.0    | 1112484676 | train      | 2025-12-17 08:30:15
1      | 231     | 4.0    | 1112484819 | train      | 2025-12-17 08:30:15
1      | 292     | 4.0    | 1112484703 | train      | 2025-12-17 08:30:15
2      | 332     | 3.5    | 1151107628 | test       | 2025-12-17 08:30:16
```

#### Statistics

```sql
-- Data distribution
SELECT 
    data_split,
    COUNT(*) as records,
    ROUND(AVG(rating), 2) as avg_rating,
    ROUND(STDDEV(rating), 2) as std_rating
FROM ratings
GROUP BY data_split;
```

**Expected Results:**
```
data_split | records  | avg_rating | std_rating
-----------|----------|------------|------------
train      | 700,000  | 3.54       | 1.07
test       | 300,000  | 3.53       | 1.06
```

---

### Table: `movies`

**Purpose:** Movie metadata and feature vectors for recommendations

**Description:** Contains movie information including titles, genres, and PCA-reduced feature embeddings for content-based filtering.

#### Schema

```sql
CREATE TABLE movies (
    movieId INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    genres VARCHAR(200),
    pca_features JSONB
);
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `movieId` | INTEGER | PRIMARY KEY | Unique movie identifier |
| `title` | VARCHAR(500) | NOT NULL | Movie title with year (e.g., "Toy Story (1995)") |
| `genres` | VARCHAR(200) | | Pipe-separated genres (e.g., "Action\|Adventure\|Sci-Fi") |
| `pca_features` | JSONB | | PCA-reduced genre embeddings (10 dimensions) |

#### Indexes

```sql
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movies_genres ON movies USING GIN(to_tsvector('english', genres));
```

**Index Rationale:**
- `title`: Fast title lookups and searches
- `genres`: Full-text search on genres using GIN index

#### Sample Data

```sql
SELECT movieId, title, genres FROM movies LIMIT 5;
```

```
movieId | title                              | genres
--------|------------------------------------|--------------------------
1       | Toy Story (1995)                  | Adventure|Animation|Children|Comedy|Fantasy
2       | Jumanji (1995)                    | Adventure|Children|Fantasy
3       | Grumpier Old Men (1995)           | Comedy|Romance
4       | Waiting to Exhale (1995)          | Comedy|Drama|Romance
5       | Father of the Bride Part II (1995)| Comedy
```

#### Statistics

```sql
-- Genre distribution
SELECT 
    unnest(string_to_array(genres, '|')) as genre,
    COUNT(*) as movie_count
FROM movies
GROUP BY genre
ORDER BY movie_count DESC
LIMIT 10;
```

---

### Table: `ratings_buffer`

**Purpose:** Staging area for new production data (continuous monitoring)

**Description:** Accumulates new user ratings that arrive in production, simulating continuous data ingestion. Used for drift detection and incremental model retraining.

#### Schema

```sql
CREATE TABLE ratings_buffer (
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    rating FLOAT NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp BIGINT NOT NULL,
    batch_id VARCHAR(50),
    ingested_at TIMESTAMP
);
```

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `userId` | INTEGER | NOT NULL | User identifier |
| `movieId` | INTEGER | NOT NULL | Movie identifier |
| `rating` | FLOAT | NOT NULL, 0.5-5.0 | Star rating |
| `timestamp` | BIGINT | NOT NULL | Original rating timestamp |
| `batch_id` | VARCHAR(50) | | Batch identifier (e.g., 'batch_w1') |
| `ingested_at` | TIMESTAMP | | When loaded by Airflow |

#### Indexes

```sql
CREATE INDEX idx_buffer_batch ON ratings_buffer(batch_id);
CREATE INDEX idx_buffer_ingested ON ratings_buffer(ingested_at);
CREATE INDEX idx_buffer_timestamp ON ratings_buffer(timestamp);
```

**Index Rationale:**
- `batch_id`: Group operations by batch
- `ingested_at`: Track ingestion timeline
- `timestamp`: Temporal analysis of new data

#### Lifecycle

```sql
-- Initially empty
SELECT COUNT(*) FROM ratings_buffer;  -- 0

-- After Week 1 ingestion
SELECT COUNT(*) FROM ratings_buffer;  -- 43,000

-- After Week 2 ingestion
SELECT COUNT(*) FROM ratings_buffer;  -- 86,000

-- After Week 3 ingestion
SELECT COUNT(*) FROM ratings_buffer;  -- 129,000

-- After retraining (cleared or merged)
DELETE FROM ratings_buffer;           -- Ready for next cycle
```

#### Sample Data

```sql
SELECT * FROM ratings_buffer LIMIT 5;
```

```
userId | movieId | rating | timestamp  | batch_id  | ingested_at
-------|---------|--------|------------|-----------|-------------------
145    | 2571    | 4.5    | 1577836800 | batch_w1  | 2025-12-18 09:15:32
145    | 318     | 5.0    | 1577923200 | batch_w1  | 2025-12-18 09:15:32
234    | 527     | 3.5    | 1578009600 | batch_w1  | 2025-12-18 09:15:32
234    | 593     | 4.0    | 1578096000 | batch_w1  | 2025-12-18 09:15:32
345    | 1196    | 4.5    | 1578182400 | batch_w3  | 2025-12-19 10:22:18
```

---

## 🔧 Metadata Tables

### Table: `ingestion_metadata`

**Purpose:** Audit trail for batch ingestion operations

**Description:** Logs every batch ingestion with record counts, timestamps, and status. Enables tracking of data pipeline operations and troubleshooting.

#### Schema

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

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `batch_id` | VARCHAR(50) | UNIQUE, NOT NULL | Batch identifier (e.g., 'batch_w1') |
| `ingestion_date` | TIMESTAMP | DEFAULT NOW | When ingestion completed |
| `record_count` | INTEGER | | Number of records ingested |
| `status` | VARCHAR(20) | | 'completed', 'failed', 'in_progress' |
| `notes` | TEXT | | Additional information or error messages |

#### Sample Data

```sql
SELECT * FROM ingestion_metadata ORDER BY ingestion_date DESC;
```

```
id | batch_id  | ingestion_date       | record_count | status    | notes
---|-----------|----------------------|--------------|-----------|---------------------------
3  | batch_w5  | 2025-12-20 11:45:22 | 43,128       | completed | Weekly batch 5 ingested
2  | batch_w3  | 2025-12-19 10:22:18 | 43,256       | completed | Weekly batch 3 ingested
1  | batch_w1  | 2025-12-18 09:15:32 | 43,256       | completed | Weekly batch 1 ingested
```

#### Usage Queries

```sql
-- Check recent ingestions
SELECT batch_id, ingestion_date, record_count, status
FROM ingestion_metadata
WHERE ingestion_date > NOW() - INTERVAL '7 days'
ORDER BY ingestion_date DESC;

-- Total records ingested
SELECT SUM(record_count) as total_ingested
FROM ingestion_metadata
WHERE status = 'completed';
```

---

### Table: `model_metrics`

**Purpose:** Track model performance over time

**Description:** Stores evaluation metrics for each model training run, enabling comparison of model versions and monitoring performance degradation.

#### Schema

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

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `model_version` | VARCHAR(50) | NOT NULL | Model identifier (MLflow run_id or version) |
| `training_date` | TIMESTAMP | DEFAULT NOW | When model was trained |
| `rmse` | FLOAT | | Root Mean Squared Error |
| `mae` | FLOAT | | Mean Absolute Error |
| `precision_at_10` | FLOAT | | Precision at K=10 for recommendations |
| `data_size` | INTEGER | | Number of ratings used for training |
| `notes` | TEXT | | Training configuration, hyperparameters |

#### Sample Data

```sql
SELECT * FROM model_metrics ORDER BY training_date DESC;
```

```
id | model_version        | training_date       | rmse | mae  | precision_at_10 | data_size | notes
---|----------------------|---------------------|------|------|-----------------|-----------|------------------
3  | run_abc123_v3       | 2025-12-20 15:30:22 | 0.82 | 0.64 | 0.76            | 829,000   | Retrained w/ buffer
2  | run_def456_v2       | 2025-12-19 14:15:10 | 0.85 | 0.67 | 0.74            | 786,000   | Added batch_w3
1  | run_ghi789_v1       | 2025-12-18 12:00:00 | 0.89 | 0.71 | 0.71            | 700,000   | Initial model
```

#### Usage Queries

```sql
-- Compare model performance over time
SELECT 
    model_version,
    training_date,
    rmse,
    mae,
    data_size,
    LAG(rmse) OVER (ORDER BY training_date) as prev_rmse,
    rmse - LAG(rmse) OVER (ORDER BY training_date) as rmse_improvement
FROM model_metrics
ORDER BY training_date DESC;

-- Best performing model
SELECT model_version, rmse, mae, precision_at_10
FROM model_metrics
ORDER BY rmse ASC
LIMIT 1;
```

---

### Table: `drift_alerts`

**Purpose:** Log data drift detection results

**Description:** Records results of statistical tests comparing baseline and new data distributions. Used to trigger retraining decisions.

#### Schema

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

#### Columns

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `alert_date` | TIMESTAMP | DEFAULT NOW | When drift check was performed |
| `feature_name` | VARCHAR(100) | | Feature/metric tested (e.g., 'rating_mean', 'rating_distribution_ks') |
| `drift_score` | FLOAT | | Calculated drift metric value |
| `threshold` | FLOAT | | Threshold for triggering alert |
| `alert_triggered` | BOOLEAN | | TRUE if drift_score exceeds threshold |
| `notes` | TEXT | | Additional context (baseline vs new values, p-values) |

#### Sample Data

```sql
SELECT * FROM drift_alerts ORDER BY alert_date DESC LIMIT 6;
```

```
id | alert_date           | feature_name             | drift_score | threshold | alert_triggered | notes
---|----------------------|--------------------------|-------------|-----------|-----------------|------------------------
6  | 2025-12-20 11:50:15 | rating_distribution_ks   | 0.067       | 0.05      | true            | KS test p-value: 0.0000
5  | 2025-12-20 11:50:15 | rating_mean              | 0.121       | 0.10      | true            | Baseline: 3.540, New: 3.968
4  | 2025-12-20 11:50:15 | rating_std               | 0.045       | 0.15      | false           | Baseline: 1.070, New: 1.118
3  | 2025-12-19 10:25:30 | rating_distribution_ks   | 0.042       | 0.05      | false           | KS test p-value: 0.0012
2  | 2025-12-19 10:25:30 | rating_mean              | 0.068       | 0.10      | false           | Baseline: 3.540, New: 3.781
1  | 2025-12-19 10:25:30 | rating_std               | 0.023       | 0.15      | false           | Baseline: 1.070, New: 1.094
```

#### Usage Queries

```sql
-- Check if retraining is needed (any recent alerts triggered?)
SELECT 
    alert_date,
    feature_name,
    drift_score,
    threshold
FROM drift_alerts
WHERE alert_triggered = TRUE
  AND alert_date > NOW() - INTERVAL '1 day'
ORDER BY alert_date DESC;

-- Drift trend over time
SELECT 
    DATE(alert_date) as date,
    feature_name,
    AVG(drift_score) as avg_drift_score,
    BOOL_OR(alert_triggered) as any_alerts
FROM drift_alerts
GROUP BY DATE(alert_date), feature_name
ORDER BY date DESC, feature_name;
```

---

## 🔗 Table Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│    ratings      │
│                 │
│ PK: -           │
│ FK: movieId ────┼────┐
└─────────────────┘    │
                       │
┌─────────────────┐    │
│ ratings_buffer  │    │
│                 │    │
│ PK: -           │    │
│ FK: movieId ────┼────┤
└─────────────────┘    │
                       │
                       ▼
              ┌─────────────────┐
              │     movies      │
              │                 │
              │ PK: movieId     │
              └─────────────────┘

┌─────────────────────┐
│ ingestion_metadata  │
│                     │
│ PK: id              │
│ UK: batch_id        │
└─────────────────────┘

┌─────────────────┐
│ model_metrics   │
│                 │
│ PK: id          │
└─────────────────┘

┌─────────────────┐
│ drift_alerts    │
│                 │
│ PK: id          │
└─────────────────┘
```

**Notes:**
- No foreign key constraints enforced (denormalized for performance)
- `movieId` logically references `movies` table
- Metadata tables are independent (logging only)

---

## 📊 Database Statistics

### Storage Usage

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Expected Results:**
```
tablename           | size    | size_bytes
--------------------|---------|------------
ratings             | 250 MB  | 262,144,000
ratings_buffer      | 30 MB   | 31,457,280
movies              | 5 MB    | 5,242,880
ingestion_metadata  | 48 kB   | 49,152
model_metrics       | 32 kB   | 32,768
drift_alerts        | 64 kB   | 65,536
```

### Record Counts

```sql
SELECT 
    'ratings' as table_name, 
    COUNT(*) as records 
FROM ratings
UNION ALL
SELECT 'ratings_buffer', COUNT(*) FROM ratings_buffer
UNION ALL
SELECT 'movies', COUNT(*) FROM movies
UNION ALL
SELECT 'ingestion_metadata', COUNT(*) FROM ingestion_metadata
UNION ALL
SELECT 'model_metrics', COUNT(*) FROM model_metrics
UNION ALL
SELECT 'drift_alerts', COUNT(*) FROM drift_alerts
ORDER BY records DESC;
```

---

## 🛠️ Maintenance Operations

### Vacuum & Analyze

```sql
-- Regular maintenance (run weekly)
VACUUM ANALYZE ratings;
VACUUM ANALYZE ratings_buffer;
VACUUM ANALYZE movies;
```

### Clear Buffer After Retraining

```sql
-- Option 1: Delete all buffer data
DELETE FROM ratings_buffer;

-- Option 2: Merge into main ratings table
INSERT INTO ratings (userId, movieId, rating, timestamp, data_split, loaded_at)
SELECT userId, movieId, rating, timestamp, 'train', NOW()
FROM ratings_buffer;

DELETE FROM ratings_buffer;
```

### Archive Old Metadata

```sql
-- Archive drift alerts older than 30 days
CREATE TABLE drift_alerts_archive AS
SELECT * FROM drift_alerts
WHERE alert_date < NOW() - INTERVAL '30 days';

DELETE FROM drift_alerts
WHERE alert_date < NOW() - INTERVAL '30 days';
```

---

## 🔍 Common Queries

### Training Pipeline Queries

```sql
-- Get training data
SELECT userId, movieId, rating, timestamp
FROM ratings
WHERE data_split = 'train'
ORDER BY timestamp;

-- Get test data
SELECT userId, movieId, rating, timestamp
FROM ratings
WHERE data_split = 'test'
ORDER BY timestamp;

-- Get combined training + buffer data (for retraining)
SELECT userId, movieId, rating, timestamp
FROM ratings
WHERE data_split = 'train'
UNION ALL
SELECT userId, movieId, rating, timestamp
FROM ratings_buffer
ORDER BY timestamp;
```

### Monitoring Queries

```sql
-- Latest drift detection results
SELECT 
    alert_date,
    feature_name,
    drift_score,
    threshold,
    alert_triggered
FROM drift_alerts
ORDER BY alert_date DESC
LIMIT 10;

-- Is retraining needed?
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '🚨 RETRAINING NEEDED'
        ELSE '✅ NO ACTION REQUIRED'
    END as recommendation
FROM drift_alerts
WHERE alert_triggered = TRUE
  AND alert_date > NOW() - INTERVAL '1 day';
```

### Analytics Queries

```sql
-- Rating distribution comparison
WITH baseline AS (
    SELECT rating, COUNT(*) as count
    FROM ratings WHERE data_split = 'train'
    GROUP BY rating
),
new_data AS (
    SELECT rating, COUNT(*) as count
    FROM ratings_buffer
    GROUP BY rating
)
SELECT 
    baseline.rating,
    baseline.count as baseline_count,
    COALESCE(new_data.count, 0) as buffer_count,
    baseline.count - COALESCE(new_data.count, 0) as difference
FROM baseline
LEFT JOIN new_data ON baseline.rating = new_data.rating
ORDER BY baseline.rating;

-- Most popular movies (by ratings count)
SELECT 
    m.title,
    m.genres,
    COUNT(*) as num_ratings,
    ROUND(AVG(r.rating), 2) as avg_rating
FROM ratings r
JOIN movies m ON r.movieId = m.movieId
WHERE r.data_split = 'train'
GROUP BY m.movieId, m.title, m.genres
ORDER BY num_ratings DESC
LIMIT 10;
```

---

## 🎯 Design Rationale

### Why This Schema?

**1. Separation of Train/Test in One Table**
- ✅ Simpler than separate tables
- ✅ Easy to switch between splits
- ✅ Maintains data lineage
- ✅ One source of truth

**2. Buffer as Staging Area**
- ✅ Clean separation from baseline
- ✅ Easy to clear after retraining
- ✅ Enables drift comparison
- ✅ Simulates production ingestion

**3. Metadata Tables for Observability**
- ✅ Audit trail for all operations
- ✅ Debugging and troubleshooting
- ✅ Performance tracking over time
- ✅ Decision logic transparency

**4. No Foreign Key Constraints**
- ✅ Better performance for bulk inserts
- ✅ Simpler data loading
- ✅ OLAP-optimized (read-heavy)
- ⚠️ Application enforces referential integrity

---

## 🔐 Security & Access

### Connection Security

```bash
# Always use SSL
sslmode=require

# Use environment variables
export NEON_CONNECTION_STRING="postgresql://..."
```

### Access Control

```sql
-- In production, create read-only user for analysts
CREATE USER analyst WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;

-- Read-write for ML pipeline
CREATE USER ml_pipeline WITH PASSWORD 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ml_pipeline;
```

---

## 📚 References

**PostgreSQL Documentation:**
- Indexes: https://www.postgresql.org/docs/15/indexes.html
- Data Types: https://www.postgresql.org/docs/15/datatype.html

**Neon Documentation:**
- Getting Started: https://neon.tech/docs/
- Connection Pooling: https://neon.tech/docs/connect/connection-pooling

**Best Practices:**
- OLAP Design: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/
- Time-series Data: https://www.timescale.com/blog/time-series-data/

---

## 🎓 Key Takeaways

The CineMatch database schema demonstrates:

✅ **MLOps-ready design** - Tables support continuous training workflows  
✅ **Observability** - Comprehensive metadata for monitoring  
✅ **Scalability** - Optimized indexes for analytical queries  
✅ **Maintainability** - Clear structure and documentation  
✅ **Production patterns** - Staging area, audit trails, versioning  

**Bottom Line:** A well-designed schema is foundational to reliable ML systems. This schema balances simplicity with production-grade practices, enabling both learning and real-world applicability.

---

**Last Updated:** December 18, 2025  
**Schema Version:** 1.0  
**Maintained By:** CineMatch Data Team  
**Next Review:** After project completion
