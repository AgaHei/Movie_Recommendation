# Drift Monitoring DAG - User Guide

## What This DAG Does

The `drift_monitoring` DAG detects when your data distribution changes significantly, indicating that your model should be retrained.

## How It Works

### Step 1: Load Baseline Statistics
- Pulls training data from `ratings` table (data_split='train')
- Calculates: mean, std, median, distribution

### Step 2: Load New Data Statistics
- Pulls new data from `ratings_buffer` table
- Calculates same statistics

### Step 3: Calculate Drift Scores
Runs 3 statistical tests:

1. **Kolmogorov-Smirnov (KS) Test**
   - Compares entire distributions
   - Threshold: 0.05
   - Detects: Overall pattern changes

2. **Mean Change**
   - Checks if average rating shifted
   - Threshold: 10% change
   - Detects: Rating inflation/deflation

3. **Standard Deviation Change**
   - Checks if variance changed
   - Threshold: 15% change
   - Detects: Rating spread changes

### Step 4: Log Alerts
- Writes results to `drift_alerts` table in Neon
- Each test gets its own row
- Marks `alert_triggered=TRUE` if drift detected

### Step 5: Generate Report
- Prints final recommendation
- If ANY test detects drift → "RETRAINING RECOMMENDED"

## Configuration

You can adjust thresholds in the DAG file:

```python
DRIFT_THRESHOLDS = {
    'ks_statistic': 0.05,      # More sensitive = lower value
    'mean_change': 0.10,        # 10% = moderate sensitivity
    'std_change': 0.15,         # 15% = less sensitive
    'count_threshold': 10000,   # Min records before checking
}
```

## How to Use

### Manual Trigger (Recommended for Testing):
1. Go to Airflow UI: http://localhost:8080
2. Find `drift_monitoring` DAG
3. Click ▶️ to trigger
4. Watch tasks execute

### Automated (Daily):
- DAG is scheduled to run daily (`schedule_interval='@daily'`)
- Automatically checks for drift every day at midnight

### After Each Run:
Check results in Neon:

```sql
-- View recent drift alerts
SELECT * FROM drift_alerts 
ORDER BY alert_date DESC 
LIMIT 10;

-- Check if retraining is needed
SELECT feature_name, alert_triggered, drift_score, notes
FROM drift_alerts
WHERE alert_date > NOW() - INTERVAL '1 day'
AND alert_triggered = TRUE;
```

## Understanding the Output

### ✅ No Drift Detected
```
✅ FINAL DECISION: NO DRIFT - CONTINUE MONITORING
```
**Meaning:** Data patterns are stable, model is still valid

### 🚨 Drift Detected
```
🚨 FINAL DECISION: DRIFT DETECTED - RETRAINING RECOMMENDED
Triggered by: Distribution shift, Mean change
```
**Meaning:** Data has changed, model performance may degrade

**Action:** Trigger retraining (next DAG will automate this)

## Expected Results with Your Data

Since you ingested batches 1, 3, and 5:
- **Likely result:** Some drift detected
- **Why:** Buffer data is from different time period than training data
- **This is good!** Demonstrates the monitoring system works

## Troubleshooting

### "No drift analysis performed (insufficient data)"
- Need at least 10,000 records in ratings_buffer
- Load more buffer batches or reduce `count_threshold`

### "No data in ratings_buffer"
- Buffer ingestion DAG hasn't run yet
- Run `buffer_ingestion_weekly` first

### Import errors (scipy, pandas)
```bash
docker-compose exec airflow-scheduler pip install scipy pandas
docker-compose restart
```

## Next Steps

After this DAG works:
1. Review drift alerts in Neon
2. Understand which metrics triggered alerts
3. Next week: Create trigger DAG that acts on these alerts

## Tips

- Run drift monitoring AFTER ingesting buffer batches
- Check logs for detailed statistics
- Adjust thresholds based on your data sensitivity needs
- In production: Would run daily after new data arrives
