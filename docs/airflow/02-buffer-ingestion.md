# Buffer Ingestion DAG - Complete Guide

## 📦 Overview

The Buffer Ingestion DAG simulates continuous data arrival in a production recommendation system. It loads weekly batches of new user ratings into the database, enabling drift detection and triggering model retraining when needed.

---

## 🎯 Purpose

In production ML systems, new data arrives continuously. This DAG simulates that process by:
- Loading batches of new ratings into `ratings_buffer` table
- Logging ingestion metadata for audit trails
- Enabling progressive drift monitoring
- Demonstrating realistic MLOps data pipeline

---

## 🏗️ Architecture

### Data Flow

```
Local PC: buffer_batches/
    ├── batch_w1.parquet (500k ratings)
    ├── batch_w3.parquet (500k ratings)
    └── batch_w5.parquet (500k ratings)
            ↓
    Airflow DAG reads files
            ↓
    Neon: ratings_buffer table
            ↓
    Metadata logged to ingestion_metadata
```

### Why Buffer Batches?

**Simulation Strategy:**
- **Week 1:** Ingest batch_w1 → Monitor → "Not enough data"
- **Week 2:** Ingest batch_w3 → Monitor → "Early drift signals"
- **Week 3:** Ingest batch_w5 → Monitor → "🚨 Drift detected! Retrain!"

This simulates **3 weeks of production operation** in a compressed timeframe.

---

## 📋 DAG Structure

### DAG ID
`buffer_ingestion_weekly`

### Schedule
`None` (Manual trigger for simulation)

In production: Would be `@weekly` or `0 0 * * 1` (every Monday)

### Tasks

The DAG creates separate tasks for each batch:

```
ingest_batch_1
    ↓
ingest_batch_3
    ↓
ingest_batch_5
    ↓
check_buffer_status
```

**Note:** For sequential simulation, modify to ingest one batch at a time.

---

## 🔧 Configuration

### Modifying for Sequential Ingestion

**Week 1 - Ingest batch_w1 only:**

```python
# In buffer_ingestion_dag.py, find this section:
batch_tasks = []
for i in [1, 3, 5]:  # Original (all batches)

# Change to:
for i in [1]:  # Week 1 - only batch 1
```

**Week 2 - Ingest batch_w3 only:**

```python
for i in [3]:  # Week 2 - only batch 3
```

**Week 3 - Ingest batch_w5 only:**

```python
for i in [5]:  # Week 3 - only batch 5
```

### File Paths

The DAG expects files at:
```
/opt/airflow/data/prepared/buffer_batches/batch_wN.parquet
```

This maps to your local:
```
your-project/data/prepared/buffer_batches/batch_wN.parquet
```

Via Docker volume mount in `docker-compose.yml`:
```yaml
volumes:
  - ../data:/opt/airflow/data
```

---

## 📊 What Each Task Does

### Task: `ingest_batch_X`

**Function:** `ingest_batch(batch_number)`

**Steps:**
1. Connects to Neon database
2. Reads batch file: `batch_wN.parquet`
3. Adds `ingested_at` timestamp
4. Inserts data into `ratings_buffer` table
5. Logs metadata to `ingestion_metadata` table
6. Verifies insertion count

**Output:**
```
====================================================================
📦 INGESTING BATCH 1
====================================================================

📂 Loading batch from: /opt/airflow/data/prepared/buffer_batches/batch_w1.parquet
✅ Loaded 43,256 ratings
   Columns: ['userId', 'movieId', 'rating', 'timestamp', 'batch_id']

⬆️  Uploading to Neon ratings_buffer table...
✅ Successfully inserted 43,256 rows into ratings_buffer

📝 Logging ingestion metadata...
✅ Metadata logged successfully

🔍 Verifying data in Neon...
✅ Verified: 500002 rows in database for batch_w1

====================================================================
🎉 BATCH 1 INGESTION COMPLETE
====================================================================
```

### Task: `check_buffer_status`

**Function:** `check_buffer_status()`

**Steps:**
1. Counts total records in `ratings_buffer`
2. Counts number of distinct batches
3. Shows ingestion history from `ingestion_metadata`

**Output:**
```
====================================================================
📊 BUFFER INGESTION STATUS
====================================================================

📈 Total records in buffer: 500002
📦 Number of batches: 1

📋 Ingestion History:
   batch_w1: 500002 records - completed - 2025-12-18 10:30:15

====================================================================
```

---

## 🚀 How to Use

### Prerequisites

1. **Buffer batch files exist:**
```bash
ls data/prepared/buffer_batches/
# Should show: batch_w1.parquet, batch_w3.parquet, batch_w5.parquet
```

2. **Airflow is running:**
```bash
cd airflow/
docker-compose ps
# All services should be "Up"
```

3. **Neon credentials configured:**
```bash
# In airflow/.env
NEON_CONNECTION_STRING=postgresql://...
```

---

### Week 1: First Batch

**Step 1: Modify DAG**
```python
# buffer_ingestion_dag.py
for i in [1]:  # Only batch 1
```

**Step 2: Trigger in Airflow UI**
1. Go to http://localhost:8080
2. Find `buffer_ingestion_weekly`
3. Click ▶️ (play button)
4. Watch tasks execute

**Step 3: Verify in Neon**
```sql
SELECT COUNT(*) FROM ratings_buffer;
-- Expected: 500002 (or similar)

SELECT * FROM ingestion_metadata;
-- Should show batch_w1 completed
```

---

### Week 2: Second Batch

**Step 1: Modify DAG**
```python
for i in [3]:  # Only batch 3
```

**Step 2: Restart Airflow (to detect change)**
```bash
docker-compose restart airflow-scheduler
# Wait 30 seconds
```

**Step 3: Trigger DAG again**

**Step 4: Verify cumulative data**
```sql
SELECT batch_id, COUNT(*) 
FROM ratings_buffer 
GROUP BY batch_id;

-- Expected:
-- batch_w1: ~500k
-- batch_w3: ~500k
-- Total: ~1M
```

---

### Week 3: Final Batch

Repeat with `for i in [5]:`

Final state:
```sql
SELECT COUNT(*) FROM ratings_buffer;
-- Expected: ~129k total
```

---

## 🗄️ Database Schema

### ratings_buffer Table

```sql
CREATE TABLE ratings_buffer (
    userId INTEGER,
    movieId INTEGER,
    rating FLOAT,
    timestamp BIGINT,
    batch_id VARCHAR(50),      -- e.g., 'batch_w1'
    ingested_at TIMESTAMP       -- When loaded by Airflow
);
```

### ingestion_metadata Table

```sql
CREATE TABLE ingestion_metadata (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(50) UNIQUE NOT NULL,
    ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    status VARCHAR(20),         -- 'completed', 'failed'
    notes TEXT
);
```

---

## 🔍 Verification Queries

### Check Current Buffer State
```sql
-- Total records
SELECT COUNT(*) as total_records FROM ratings_buffer;

-- By batch
SELECT 
    batch_id, 
    COUNT(*) as records,
    MIN(timestamp) as earliest_rating,
    MAX(timestamp) as latest_rating
FROM ratings_buffer
GROUP BY batch_id
ORDER BY batch_id;
```

### Check Ingestion History
```sql
SELECT 
    batch_id,
    ingestion_date,
    record_count,
    status
FROM ingestion_metadata
ORDER BY ingestion_date DESC;
```

### Verify Data Quality
```sql
-- Check for duplicates (shouldn't have any)
SELECT userId, movieId, timestamp, COUNT(*)
FROM ratings_buffer
GROUP BY userId, movieId, timestamp
HAVING COUNT(*) > 1;

-- Check rating range (should be 0.5 to 5.0)
SELECT 
    MIN(rating) as min_rating,
    MAX(rating) as max_rating,
    AVG(rating) as avg_rating
FROM ratings_buffer;
```

---

## ⚠️ Troubleshooting

### Error: "Batch file not found"

**Symptom:**
```
FileNotFoundError: /opt/airflow/data/prepared/buffer_batches/batch_w1.parquet
```

**Solutions:**

1. **Check files exist locally:**
```bash
ls your-project/data/prepared/buffer_batches/
```

2. **Verify Docker volume mount:**
```bash
docker-compose exec airflow-scheduler ls /opt/airflow/data/prepared/buffer_batches/
```

3. **Check docker-compose.yml:**
```yaml
volumes:
  - ../data:/opt/airflow/data  # Correct relative path?
```

4. **Restart Airflow:**
```bash
docker-compose down
docker-compose up -d
```

---

### Error: "Duplicate key violation"

**Symptom:**
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
```

**Cause:** Trying to ingest the same batch twice

**Solution:**

```sql
-- Check what's already ingested
SELECT * FROM ingestion_metadata;

-- If re-running, delete the batch first
DELETE FROM ratings_buffer WHERE batch_id = 'batch_w1';
DELETE FROM ingestion_metadata WHERE batch_id = 'batch_w1';
```

---

### Error: "Connection to Neon failed"

**Symptom:**
```
OperationalError: could not connect to server
```

**Solutions:**

1. **Check .env file:**
```bash
cat airflow/.env | grep NEON_CONNECTION_STRING
```

2. **Test connection:**
```bash
docker-compose exec airflow-scheduler python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('NEON_CONNECTION_STRING'))
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('✅ Connection successful!')
"
```

3. **Verify Neon is accessible:**
- Check Neon dashboard (console.neon.tech)
- Verify project isn't suspended
- Check connection string is correct

---

### Error: "Disk full" (Neon storage limit)

**Symptom:**
```
psycopg2.errors.DiskFull: project size limit (512 MB) has been exceeded
```

**Solution:**

Reduce data or clear buffer:

```sql
-- Check current usage
SELECT 
    'ratings' as table_name, 
    pg_size_pretty(pg_total_relation_size('ratings')) as size
UNION ALL
SELECT 
    'ratings_buffer', 
    pg_size_pretty(pg_total_relation_size('ratings_buffer'));

-- Option 1: Clear old buffer data
DELETE FROM ratings_buffer;

-- Option 2: Reduce initial dataset (reload with smaller sample)
```

---

## 📈 Best Practices

### Sequential Ingestion (Recommended for Simulation)

✅ **DO:**
- Modify DAG to ingest one batch at a time
- Run drift monitoring after each batch
- Document results between ingestions
- Clear buffer after retraining (in production)

❌ **DON'T:**
- Ingest all batches at once (defeats simulation purpose)
- Skip drift monitoring between batches
- Leave old data in buffer indefinitely

---

### Production Considerations

In a real production system:

**Scheduling:**
```python
schedule_interval='@weekly'  # Automatic weekly ingestion
```

**Data Source:**
- Real-time: Kafka/Kinesis stream
- Batch: S3/Cloud Storage
- Database: Production OLTP system

**Error Handling:**
```python
'retries': 3,
'retry_delay': timedelta(minutes=10),
'on_failure_callback': send_slack_alert
```

**Monitoring:**
- Track ingestion lag
- Monitor data quality metrics
- Alert on failures
- Dashboard for buffer size

---

## 🔗 Integration with Other DAGs

### Workflow Sequence

```
1. buffer_ingestion_weekly (this DAG)
        ↓
   Loads new data
        ↓
2. drift_monitoring
        ↓
   Detects changes
        ↓
3. trigger_retraining (if drift detected)
        ↓
   Starts model training
        ↓
4. Model retrains → deploys → buffer cleared
```

### Triggering Next Steps

**Manual (Current):**
- Run buffer ingestion
- Wait for completion
- Manually trigger drift monitoring

**Automated (Future):**
```python
# In buffer_ingestion_dag.py
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

trigger_monitoring = TriggerDagRunOperator(
    task_id='trigger_drift_monitoring',
    trigger_dag_id='drift_monitoring',
    dag=dag,
)

status_task >> trigger_monitoring
```

---

## 📝 Logging & Monitoring

### View Task Logs

**In Airflow UI:**
1. Click on DAG run
2. Click on task (e.g., `ingest_batch_1`)
3. Click "Log" button
4. Scroll to see detailed output

**Key log sections:**
- File loading confirmation
- Upload progress
- Metadata logging
- Verification counts

### Monitor Performance

```sql
-- Ingestion speed (records per second)
SELECT 
    batch_id,
    record_count,
    EXTRACT(EPOCH FROM (
        LAG(ingestion_date) OVER (ORDER BY ingestion_date) - ingestion_date
    )) / record_count as records_per_second
FROM ingestion_metadata
ORDER BY ingestion_date;
```

---

## 🎓 Learning Outcomes

By working with this DAG, you demonstrate:

✅ **Data Engineering:**
- Batch data ingestion
- Database operations
- Data validation

✅ **MLOps:**
- Continuous data pipeline
- Production simulation
- Metadata tracking

✅ **Airflow:**
- DAG creation
- Task dependencies
- Error handling
- Logging

✅ **System Design:**
- Separation of concerns (ingest vs. monitor)
- Incremental processing
- Audit trails

---

## 📚 Related Documentation

- [Airflow Setup Guide](01-airflow-setup.md)
- [Drift Monitoring Guide](03-drift-monitoring.md)
- [Database Schema](../data/neon-schema.md)
- [3-Week Simulation Log](../mlops/weekly-simulation-log.md)

---

## 🎯 Summary

The Buffer Ingestion DAG is the **foundation of your continuous monitoring system**. It:
- ✅ Simulates realistic data arrival patterns
- ✅ Enables progressive drift detection
- ✅ Provides audit trails via metadata
- ✅ Demonstrates production-grade data engineering

**Key Takeaway:** In production ML systems, data ingestion isn't a one-time event—it's a continuous process that requires careful orchestration, monitoring, and integration with downstream ML pipelines.

---

**Last Updated:** December 18, 2025  
**Maintained By:** CineMatch Data Pipeline Team
