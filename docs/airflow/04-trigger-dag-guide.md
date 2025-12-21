# Mock Training Trigger DAG - User Guide

## 🎯 Purpose

This DAG checks drift alerts and makes intelligent decisions about when to trigger model retraining. This is a **MOCK version** that logs decisions without actually calling GitHub Actions - perfect for testing and development before your teammate's training pipeline is ready!

---

## 🏗️ How It Works

### Decision Flow

```
Start
  ↓
┌──────────────────────────┐
│ Check Drift Alerts       │ ← Query drift_alerts table
│ (Last 7 days)            │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Check Buffer Size        │ ← Query ratings_buffer table
│ (Need 50k+ ratings)      │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Evaluate Criteria        │ ← Decision logic
│ All conditions met?      │
└──────────┬───────────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
  YES           NO
     │           │
     ▼           ▼
┌─────────┐  ┌──────────┐
│ TRIGGER │  │ NO ACTION│
│  MOCK   │  │  NEEDED  │
└─────────┘  └──────────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌────────────┐
    │  Summary   │
    │  Report    │
    └────────────┘
```

---

## ⚙️ Retraining Criteria

The DAG checks **3 conditions** before triggering:

### 1. Recent Drift Checks Exist
- **Lookback:** Last 7 days (168 hours)
- **Source:** `drift_alerts` table
- **Purpose:** Ensure monitoring is active

### 2. Drift Alerts Triggered
- **Minimum:** At least 1 alert with `alert_triggered = TRUE`
- **Features checked:** KS test, mean, std
- **Purpose:** Confirm actual drift detected

### 3. Sufficient Buffer Data
- **Minimum:** 50,000 new ratings
- **Source:** `ratings_buffer` table
- **Purpose:** Enough data to improve model

**All 3 must be TRUE to trigger retraining!**

---

## 📊 Tasks Breakdown

### Task 1: `check_drift_alerts`
**What it does:**
- Queries `drift_alerts` from last 7 days
- Counts how many alerts triggered
- Shows which features drifted

**Output example:**
```
📋 Recent Drift Checks:
   2025-12-21 14:54 | rating_distribution_ks  | Score: 0.0975 | Threshold: 0.0500 | 🚨 TRIGGERED
   2025-12-21 14:54 | rating_mean             | Score: 0.0450 | Threshold: 0.1000 | ✅ OK
   2025-12-21 14:54 | rating_std              | Score: 0.0120 | Threshold: 0.1500 | ✅ OK

🚨 Triggered Alerts: 1
   Drift detected in:
   • rating_distribution_ks: Score 0.0975 > Threshold 0.0500
```

---

### Task 2: `check_buffer_size`
**What it does:**
- Counts total ratings in `ratings_buffer`
- Shows batch breakdown
- Compares to minimum threshold

**Output example:**
```
📊 Current buffer size: 700,000 ratings
📏 Minimum required: 50,000 ratings
✅ Buffer size is SUFFICIENT for retraining

📦 Buffer Batches:
   batch_w1: 100,000 ratings
   batch_w2: 100,000 ratings
   batch_w3: 100,000 ratings
   batch_w4: 100,000 ratings
   batch_w5: 100,000 ratings
   batch_w6: 100,000 ratings
   batch_w7: 100,000 ratings
```

---

### Task 3: `evaluate_criteria`
**What it does:**
- Combines results from Tasks 1 & 2
- Makes final decision
- Branches to appropriate action

**Output example (TRIGGER):**
```
📋 Decision Criteria:

   1. Recent drift checks exist?
      Status: ✅ YES

   2. Drift alerts triggered?
      Count: 1
      Required: 1
      Status: ✅ YES

   3. Sufficient buffer data?
      Size: 700,000 ratings
      Required: 50,000 ratings
      Status: ✅ YES

======================================================================
🚨 DECISION: TRIGGER RETRAINING
======================================================================

✅ All criteria met!
   • Drift detected: 1 alert(s)
   • Data available: 700,000 ratings
   • Action: Initiate model retraining
```

---

### Task 4a: `trigger_retraining_mock` (If criteria met)
**What it does:**
- Prints what WOULD be sent to GitHub Actions
- Logs decision to `retraining_decisions` table
- Shows next steps

**Output example:**
```
🎬 MOCK RETRAINING TRIGGER

📝 This is a MOCK trigger - no actual GitHub Actions call
   In production, this would:
   1. Call GitHub Actions API
   2. Trigger model_training.yml workflow
   3. Pass drift information as parameters

🔧 Mock GitHub Actions Call:

   URL: https://api.github.com/repos/YOUR_USER/cinematch/actions/workflows/model_training.yml/dispatches
   Method: POST
   Headers:
      Authorization: token GITHUB_TOKEN
      Accept: application/vnd.github.v3+json

   Payload:
      ref: main
      inputs:
        reason: drift_detected
        drift_score: 0.0975
        buffer_size: 700000

✅ Decision logged to retraining_decisions table

📊 Summary:
   • Drift detected: rating_distribution_ks
   • Drift score: 0.0975
   • Buffer size: 700,000 ratings
   • Action: MOCK trigger logged

💡 Next Steps:
   1. Wait for teammate to finish training pipeline
   2. Upgrade this DAG to call real GitHub Actions API
   3. Test end-to-end retraining workflow
```

---

### Task 4b: `no_retraining_needed` (If criteria NOT met)
**What it does:**
- Logs that no action was taken
- Explains which criteria failed
- Gives recommendations

**Output example:**
```
✅ NO RETRAINING NEEDED

✅ Decision logged to retraining_decisions table

📊 Current Status:
   • Triggered alerts: 0
   • Buffer size: 35,000 ratings
   • Action: Continue monitoring

💡 Recommendation:
   • Keep ingesting new batches
   • Run drift_monitoring after each batch
   • This DAG will auto-trigger when criteria met
```

---

### Task 5: `generate_summary`
**What it does:**
- Shows history of recent decisions
- Provides final status summary

**Output example:**
```
📋 RETRAINING TRIGGER SUMMARY REPORT

📊 Recent Retraining Decisions:
   🚨 2025-12-21 15:30 | trigger_mock    | Buffer: 700,000 | Drift: 0.0975
   ✅ 2025-12-20 10:15 | no_action       | Buffer: 500,000 | Drift: N/A
   ✅ 2025-12-19 09:45 | no_action       | Buffer: 300,000 | Drift: N/A

🎯 FINAL STATUS: RETRAINING TRIGGERED (MOCK)
```

---

## 🚀 How to Use

### First Time Setup

1. **Copy DAG to Airflow folder:**
```bash
cp trigger_retraining_dag.py your-project/airflow/dags/
```

2. **Wait for Airflow to detect it** (~30 seconds)

3. **Check in Airflow UI:**
- Go to http://localhost:8080
- Look for DAG: `trigger_retraining_mock`
- Should appear with tag: `mock`

---

### Running the DAG

**Scenario 1: After Detecting Drift**
```
1. Run drift_monitoring DAG
2. Check results: SELECT * FROM drift_alerts WHERE alert_triggered = TRUE;
3. If drift detected → Run trigger_retraining_mock
4. Watch it make intelligent decision!
```

**Scenario 2: Testing Decision Logic**
```
1. Run trigger_retraining_mock anytime
2. It checks current drift_alerts state
3. Makes decision based on latest data
```

---

### Expected Results (Your Current State)

**Given your drift:**
- Alert #148: KS = 0.0975 (TRIGGERED ✅)
- Buffer: 700k ratings (SUFFICIENT ✅)

**Expected Decision: 🚨 TRIGGER RETRAINING (MOCK)**

The DAG will:
1. ✅ Find your drift alert
2. ✅ Confirm sufficient data
3. ✅ Print mock GitHub Actions call
4. ✅ Log to `retraining_decisions` table

---

## 🗄️ Database Tables

### New Table: `retraining_decisions`

**Auto-created by DAG:**
```sql
CREATE TABLE retraining_decisions (
    id SERIAL PRIMARY KEY,
    decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decision VARCHAR(20),
    reason TEXT,
    buffer_size INTEGER,
    drift_score FLOAT,
    notes TEXT
);
```

**Check decisions:**
```sql
SELECT * FROM retraining_decisions 
ORDER BY decision_date DESC;
```

**Example data:**
```
id | decision_date        | decision     | reason          | buffer_size | drift_score | notes
---|----------------------|--------------|-----------------|-------------|-------------|------------------
1  | 2025-12-21 15:30:00 | trigger_mock | drift_detected  | 700,000     | 0.0975      | MOCK: Would trigger...
```

---

## 🔄 Upgrading to Production Version

When your teammate's training pipeline is ready, you'll upgrade this DAG in **3 simple steps**:

### Step 1: Get GitHub Token

```bash
# Create Personal Access Token
# GitHub → Settings → Developer Settings → Personal Access Tokens
# Scopes: repo, workflow
```

### Step 2: Add to Airflow `.env`

```bash
# In airflow/.env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=cinematch
```

### Step 3: Replace Mock Function

**Change this function:**
```python
def trigger_retraining_mock(**context):
    # Current: Just prints mock call
    print("MOCK: Would call GitHub...")
```

**To this:**
```python
def trigger_retraining_production(**context):
    import requests
    
    github_token = os.getenv('GITHUB_TOKEN')
    repo_owner = os.getenv('GITHUB_REPO_OWNER')
    repo_name = os.getenv('GITHUB_REPO_NAME')
    
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/model_training.yml/dispatches'
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    data = {
        'ref': 'main',
        'inputs': {
            'reason': 'drift_detected',
            'drift_score': str(drift_alerts[0]['drift_score']),
            'buffer_size': str(buffer_size)
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 204:
        print("✅ GitHub Actions workflow triggered successfully!")
    else:
        print(f"❌ Failed: {response.status_code}")
        raise Exception("Workflow trigger failed")
```

**That's it!** The rest stays the same.

---

## 🎯 Verification Queries

### Check if DAG made correct decision

```sql
-- View your drift that triggered
SELECT * FROM drift_alerts 
WHERE alert_triggered = TRUE
ORDER BY alert_date DESC
LIMIT 3;

-- View decision made by DAG
SELECT * FROM retraining_decisions
ORDER BY decision_date DESC
LIMIT 1;

-- Verify buffer size
SELECT 
    COUNT(*) as total_ratings,
    COUNT(DISTINCT batch_id) as num_batches
FROM ratings_buffer;
```

---

## 📊 Testing Scenarios

### Scenario 1: Full Trigger (Your Current State)
```
Drift: YES (KS = 0.0975)
Buffer: 700k ratings
Expected: 🚨 TRIGGER
```

### Scenario 2: Drift but Not Enough Data
```
Drift: YES
Buffer: 30k ratings (< 50k threshold)
Expected: ✅ NO ACTION (need more data)
```

### Scenario 3: Enough Data but No Drift
```
Drift: NO
Buffer: 100k ratings
Expected: ✅ NO ACTION (no drift detected)
```

### Scenario 4: No Recent Drift Checks
```
drift_alerts: Empty (or > 7 days old)
Expected: ✅ NO ACTION (run drift_monitoring first)
```

---

## 🎓 Key Concepts Demonstrated

This DAG shows professional MLOps practices:

✅ **Intelligent Decision Making** - Multiple criteria, not just one signal  
✅ **Audit Trail** - All decisions logged to database  
✅ **Branching Logic** - Different paths based on conditions  
✅ **Mock Testing** - Test logic before production integration  
✅ **Clear Logging** - Detailed output for debugging  
✅ **Configurable Thresholds** - Easy to adjust criteria  

---

## 💡 Tips

**Before Each Run:**
1. Check your drift alerts are recent (`< 7 days`)
2. Verify buffer has data
3. Clear old test data if needed

**After Each Run:**
1. Check `retraining_decisions` table
2. Read the detailed logs in Airflow
3. Verify decision matches your expectations

**For Presentation:**
1. Run with drift detected → Show "TRIGGER" decision
2. Show `retraining_decisions` table
3. Explain upgrade path to production
4. Demo decision criteria clearly

---

## 🚨 Troubleshooting

### "No drift alerts found"
**Solution:** Run `drift_monitoring` DAG first

### "Buffer size insufficient"
**Solution:** Ingest more batches or lower threshold

### "Table retraining_decisions doesn't exist"
**Solution:** DAG creates it automatically on first run

### "Decision seems wrong"
**Solution:** Check thresholds in DAG code, verify drift_alerts data

---

## 📚 Related Documentation

- [Drift Monitoring Guide](03-drift-monitoring.md)
- [Buffer Ingestion Guide](02-buffer-ingestion.md)
- [Architecture Overview](../mlops/architecture-diagram.md)

---

**Last Updated:** December 21, 2025  
**Version:** 1.0 (Mock)  
**Next Version:** Production (with GitHub Actions integration)  
**Status:** ✅ Ready for Testing
