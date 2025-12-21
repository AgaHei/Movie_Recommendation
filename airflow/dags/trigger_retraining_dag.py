"""
Training Trigger DAG (Mock Version)
Checks drift alerts and makes retraining decisions
MOCK: Logs decision without actually triggering GitHub Actions
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import pandas as pd
import os

# Default arguments
default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'trigger_retraining_mock',
    default_args=default_args,
    description='Check drift alerts and make retraining decisions (MOCK - no actual trigger)',
    schedule_interval=None,  # Manual trigger (or @daily in production)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['training', 'cinematch', 'trigger', 'mock'],
)

# Retraining criteria thresholds
RETRAINING_CRITERIA = {
    'min_buffer_size': 50000,       # Need at least 50k new ratings
    'drift_lookback_hours': 168,    # Check drift alerts from last 7 days
    'min_alerts_triggered': 1,      # At least 1 alert must be triggered
}

def check_drift_alerts(**context):
    """
    Check recent drift alerts to see if retraining should be triggered
    """
    print(f"\n{'='*70}")
    print(f"🔍 CHECKING DRIFT ALERTS FOR RETRAINING DECISION")
    print(f"{'='*70}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Query recent drift alerts
    lookback_hours = RETRAINING_CRITERIA['drift_lookback_hours']
    
    print(f"📅 Lookback period: Last {lookback_hours} hours ({lookback_hours//24} days)")
    
    df_alerts = pd.read_sql(f"""
        SELECT 
            id,
            alert_date,
            feature_name,
            drift_score,
            threshold,
            alert_triggered,
            notes
        FROM drift_alerts
        WHERE alert_date > NOW() - INTERVAL '{lookback_hours} hours'
        ORDER BY alert_date DESC
    """, engine)
    
    print(f"\n📊 Found {len(df_alerts)} drift checks in the last {lookback_hours//24} days")
    
    if len(df_alerts) == 0:
        print("⚠️  No recent drift checks found")
        print("   Recommendation: Run drift_monitoring DAG first\n")
        context['ti'].xcom_push(key='alerts_found', value=False)
        context['ti'].xcom_push(key='drift_alerts', value=[])
        return
    
    # Show all alerts
    print(f"\n📋 Recent Drift Checks:")
    for idx, row in df_alerts.iterrows():
        status = "🚨 TRIGGERED" if row['alert_triggered'] else "✅ OK"
        print(f"   {row['alert_date'].strftime('%Y-%m-%d %H:%M')} | "
              f"{row['feature_name']:25s} | "
              f"Score: {row['drift_score']:.4f} | "
              f"Threshold: {row['threshold']:.4f} | "
              f"{status}")
    
    # Filter for triggered alerts
    triggered = df_alerts[df_alerts['alert_triggered'] == True]
    
    print(f"\n🚨 Triggered Alerts: {len(triggered)}")
    
    if len(triggered) > 0:
        print(f"\n   Drift detected in:")
        for idx, row in triggered.iterrows():
            print(f"   • {row['feature_name']}: "
                  f"Score {row['drift_score']:.4f} > Threshold {row['threshold']:.4f}")
            print(f"     ({row['notes']})")
    
    # Store results for next task
    context['ti'].xcom_push(key='alerts_found', value=len(df_alerts) > 0)
    context['ti'].xcom_push(key='num_triggered', value=len(triggered))
    
    # Convert to dict and handle Timestamp serialization
    if len(triggered) > 0:
        triggered_dict = triggered.copy()
        # Convert timestamp columns to string for JSON serialization
        if 'alert_date' in triggered_dict.columns:
            triggered_dict['alert_date'] = triggered_dict['alert_date'].astype(str)
        context['ti'].xcom_push(key='drift_alerts', value=triggered_dict.to_dict('records'))
    else:
        context['ti'].xcom_push(key='drift_alerts', value=[])
    
    print(f"\n{'='*70}\n")

def check_buffer_size(**context):
    """
    Check if we have enough new data in buffer to justify retraining
    """
    print(f"\n{'='*70}")
    print(f"📦 CHECKING BUFFER SIZE")
    print(f"{'='*70}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Count buffer records
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as count FROM ratings_buffer"))
        buffer_size = result.fetchone()[0]
    
    print(f"📊 Current buffer size: {buffer_size:,} ratings")
    print(f"📏 Minimum required: {RETRAINING_CRITERIA['min_buffer_size']:,} ratings")
    
    sufficient = buffer_size >= RETRAINING_CRITERIA['min_buffer_size']
    
    if sufficient:
        print(f"✅ Buffer size is SUFFICIENT for retraining")
    else:
        print(f"⚠️  Buffer size is INSUFFICIENT")
        print(f"   Need {RETRAINING_CRITERIA['min_buffer_size'] - buffer_size:,} more ratings")
    
    # Get batch breakdown
    df_batches = pd.read_sql("""
        SELECT 
            batch_id,
            COUNT(*) as count,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest
        FROM ratings_buffer
        GROUP BY batch_id
        ORDER BY batch_id
    """, engine)
    
    if len(df_batches) > 0:
        print(f"\n📦 Buffer Batches:")
        for idx, row in df_batches.iterrows():
            print(f"   {row['batch_id']}: {row['count']:,} ratings")
    
    # Store result
    context['ti'].xcom_push(key='buffer_size', value=buffer_size)
    context['ti'].xcom_push(key='buffer_sufficient', value=sufficient)
    
    print(f"\n{'='*70}\n")

def evaluate_retraining_criteria(**context):
    """
    Combine all criteria to make final retraining decision
    """
    print(f"\n{'='*70}")
    print(f"⚖️  EVALUATING RETRAINING CRITERIA")
    print(f"{'='*70}\n")
    
    # Get results from previous tasks
    alerts_found = context['ti'].xcom_pull(key='alerts_found', task_ids='check_drift_alerts')
    num_triggered = context['ti'].xcom_pull(key='num_triggered', task_ids='check_drift_alerts')
    buffer_size = context['ti'].xcom_pull(key='buffer_size', task_ids='check_buffer_size')
    buffer_sufficient = context['ti'].xcom_pull(key='buffer_sufficient', task_ids='check_buffer_size')
    
    print(f"📋 Decision Criteria:")
    print(f"\n   1. Recent drift checks exist?")
    print(f"      Status: {'✅ YES' if alerts_found else '❌ NO'}")
    
    print(f"\n   2. Drift alerts triggered?")
    print(f"      Count: {num_triggered}")
    print(f"      Required: {RETRAINING_CRITERIA['min_alerts_triggered']}")
    print(f"      Status: {'✅ YES' if num_triggered >= RETRAINING_CRITERIA['min_alerts_triggered'] else '❌ NO'}")
    
    print(f"\n   3. Sufficient buffer data?")
    print(f"      Size: {buffer_size:,} ratings")
    print(f"      Required: {RETRAINING_CRITERIA['min_buffer_size']:,} ratings")
    print(f"      Status: {'✅ YES' if buffer_sufficient else '❌ NO'}")
    
    # Make decision
    should_retrain = (
        alerts_found and
        num_triggered >= RETRAINING_CRITERIA['min_alerts_triggered'] and
        buffer_sufficient
    )
    
    print(f"\n{'='*70}")
    if should_retrain:
        print(f"🚨 DECISION: TRIGGER RETRAINING")
        print(f"{'='*70}")
        print(f"\n✅ All criteria met!")
        print(f"   • Drift detected: {num_triggered} alert(s)")
        print(f"   • Data available: {buffer_size:,} ratings")
        print(f"   • Action: Initiate model retraining")
    else:
        print(f"✅ DECISION: NO RETRAINING NEEDED")
        print(f"{'='*70}")
        print(f"\n   Criteria not met:")
        if not alerts_found:
            print(f"   ❌ No drift checks found")
        if num_triggered < RETRAINING_CRITERIA['min_alerts_triggered']:
            print(f"   ❌ No drift alerts triggered")
        if not buffer_sufficient:
            print(f"   ❌ Insufficient buffer data")
        print(f"\n   Action: Continue monitoring")
    
    print(f"\n{'='*70}\n")
    
    # Store decision
    context['ti'].xcom_push(key='should_retrain', value=should_retrain)
    
    # Return task_id for branching
    return 'trigger_retraining_mock' if should_retrain else 'no_retraining_needed'

def trigger_retraining_mock(**context):
    """
    MOCK: Log what would happen if we triggered GitHub Actions
    In production version, this calls GitHub API
    """
    print(f"\n{'='*70}")
    print(f"🎬 MOCK RETRAINING TRIGGER")
    print(f"{'='*70}\n")
    
    print(f"📝 This is a MOCK trigger - no actual GitHub Actions call")
    print(f"   In production, this would:")
    print(f"   1. Call GitHub Actions API")
    print(f"   2. Trigger model_training.yml workflow")
    print(f"   3. Pass drift information as parameters\n")
    
    # Get context
    drift_alerts = context['ti'].xcom_pull(key='drift_alerts', task_ids='check_drift_alerts')
    buffer_size = context['ti'].xcom_pull(key='buffer_size', task_ids='check_buffer_size')
    
    # Safety check
    if not drift_alerts or len(drift_alerts) == 0:
        print(f"⚠️  No drift alerts found in context")
        drift_score = 0.0
        feature_name = "unknown"
    else:
        drift_score = drift_alerts[0]['drift_score']
        feature_name = drift_alerts[0]['feature_name']
    
    print(f"🔧 Mock GitHub Actions Call:")
    print(f"\n   URL: https://api.github.com/repos/YOUR_USER/cinematch/actions/workflows/model_training.yml/dispatches")
    print(f"   Method: POST")
    print(f"   Headers:")
    print(f"      Authorization: token GITHUB_TOKEN")
    print(f"      Accept: application/vnd.github.v3+json")
    print(f"\n   Payload:")
    print(f"      ref: main")
    print(f"      inputs:")
    print(f"        reason: drift_detected")
    print(f"        drift_score: {drift_score:.4f}")
    print(f"        buffer_size: {buffer_size}")
    
    # Log decision to database
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Create table if doesn't exist
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS retraining_decisions (
                id SERIAL PRIMARY KEY,
                decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                decision VARCHAR(20),
                reason TEXT,
                buffer_size INTEGER,
                drift_score FLOAT,
                notes TEXT
            )
        """))
    
    # Log decision
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO retraining_decisions 
            (decision, reason, buffer_size, drift_score, notes)
            VALUES (:decision, :reason, :buffer_size, :drift_score, :notes)
        """), {
            'decision': 'trigger_mock',
            'reason': 'drift_detected',
            'buffer_size': buffer_size,
            'drift_score': drift_score,
            'notes': f"MOCK: Would trigger GitHub Actions. Feature: {feature_name}"
        })
    
    print(f"\n✅ Decision logged to retraining_decisions table")
    
    print(f"\n{'='*70}")
    print(f"🎯 MOCK TRIGGER COMPLETE")
    print(f"{'='*70}")
    print(f"\n📊 Summary:")
    print(f"   • Drift detected: {feature_name}")
    print(f"   • Drift score: {drift_score:.4f}")
    print(f"   • Buffer size: {buffer_size:,} ratings")
    print(f"   • Action: MOCK trigger logged")
    print(f"\n💡 Next Steps:")
    print(f"   1. Wait for teammate to finish training pipeline")
    print(f"   2. Upgrade this DAG to call real GitHub Actions API")
    print(f"   3. Test end-to-end retraining workflow")
    print(f"\n{'='*70}\n")

def no_retraining_needed(**context):
    """
    Log that no retraining was needed
    """
    print(f"\n{'='*70}")
    print(f"✅ NO RETRAINING NEEDED")
    print(f"{'='*70}\n")
    
    buffer_size = context['ti'].xcom_pull(key='buffer_size', task_ids='check_buffer_size')
    num_triggered = context['ti'].xcom_pull(key='num_triggered', task_ids='check_drift_alerts')
    
    # Log decision
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Create table if doesn't exist
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS retraining_decisions (
                id SERIAL PRIMARY KEY,
                decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                decision VARCHAR(20),
                reason TEXT,
                buffer_size INTEGER,
                drift_score FLOAT,
                notes TEXT
            )
        """))
    
    # Log decision
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO retraining_decisions 
            (decision, reason, buffer_size, drift_score, notes)
            VALUES (:decision, :reason, :buffer_size, :drift_score, :notes)
        """), {
            'decision': 'no_action',
            'reason': 'criteria_not_met',
            'buffer_size': buffer_size,
            'drift_score': None,
            'notes': f"No retraining needed. Triggered alerts: {num_triggered}, Buffer: {buffer_size:,}"
        })
    
    print(f"✅ Decision logged to retraining_decisions table")
    print(f"\n📊 Current Status:")
    print(f"   • Triggered alerts: {num_triggered}")
    print(f"   • Buffer size: {buffer_size:,} ratings")
    print(f"   • Action: Continue monitoring")
    print(f"\n💡 Recommendation:")
    print(f"   • Keep ingesting new batches")
    print(f"   • Run drift_monitoring after each batch")
    print(f"   • This DAG will auto-trigger when criteria met")
    print(f"\n{'='*70}\n")

def generate_summary_report(**context):
    """
    Generate final summary report
    """
    print(f"\n{'='*70}")
    print(f"📋 RETRAINING TRIGGER SUMMARY REPORT")
    print(f"{'='*70}\n")
    
    should_retrain = context['ti'].xcom_pull(key='should_retrain', task_ids='evaluate_criteria')
    
    # Query recent decisions
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    df_decisions = pd.read_sql("""
        SELECT 
            decision_date,
            decision,
            reason,
            buffer_size,
            drift_score
        FROM retraining_decisions
        ORDER BY decision_date DESC
        LIMIT 5
    """, engine)
    
    print(f"📊 Recent Retraining Decisions:")
    if len(df_decisions) > 0:
        for idx, row in df_decisions.iterrows():
            date_str = row['decision_date'].strftime('%Y-%m-%d %H:%M')
            decision_icon = "🚨" if row['decision'] == 'trigger_mock' else "✅"
            print(f"   {decision_icon} {date_str} | {row['decision']:15s} | "
                  f"Buffer: {row['buffer_size']:,} | "
                  f"Drift: {row['drift_score']:.4f}" if row['drift_score'] else "Drift: N/A")
    else:
        print(f"   No previous decisions recorded")
    
    print(f"\n{'='*70}")
    if should_retrain:
        print(f"🎯 FINAL STATUS: RETRAINING TRIGGERED (MOCK)")
    else:
        print(f"🎯 FINAL STATUS: NO ACTION - CONTINUE MONITORING")
    print(f"{'='*70}\n")

# Define tasks
task_check_alerts = PythonOperator(
    task_id='check_drift_alerts',
    python_callable=check_drift_alerts,
    dag=dag,
)

task_check_buffer = PythonOperator(
    task_id='check_buffer_size',
    python_callable=check_buffer_size,
    dag=dag,
)

task_evaluate = BranchPythonOperator(
    task_id='evaluate_criteria',
    python_callable=evaluate_retraining_criteria,
    dag=dag,
)

task_trigger_mock = PythonOperator(
    task_id='trigger_retraining_mock',
    python_callable=trigger_retraining_mock,
    dag=dag,
)

task_no_retrain = PythonOperator(
    task_id='no_retraining_needed',
    python_callable=no_retraining_needed,
    dag=dag,
)

task_join = EmptyOperator(
    task_id='join',
    trigger_rule='none_failed_min_one_success',
    dag=dag,
)

task_summary = PythonOperator(
    task_id='generate_summary',
    python_callable=generate_summary_report,
    dag=dag,
)

# Set dependencies
[task_check_alerts, task_check_buffer] >> task_evaluate
task_evaluate >> [task_trigger_mock, task_no_retrain]
[task_trigger_mock, task_no_retrain] >> task_join >> task_summary
