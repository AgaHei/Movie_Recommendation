"""
Training Trigger DAG (Operational Version)
Checks drift alerts and makes retraining decisions
Triggers actual model retraining when criteria are met
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator, ShortCircuitOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import pandas as pd
import os
import subprocess
from pathlib import Path

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
    'trigger_retraining_dag',
    default_args=default_args,
    description='Check drift alerts and trigger actual model retraining',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['training', 'cinematch', 'trigger', 'operational'],
)

# Training configuration
TRAINING_CONFIG = {
    'cinematch_root': os.getenv('CINEMATCH_ROOT', '/opt/airflow/cinematch'),
    'training_script': 'mlflow_training/train_mlflow.py',
    'data_output_dir': '/tmp/training_data',
}

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
    return 'export_training_data' if should_retrain else 'no_retraining_needed'

def export_training_data(**context):
    """
    Export data from Neon database for training
    """
    print(f"\n{'='*70}")
    print(f"📤 EXPORTING TRAINING DATA FROM NEON")
    print(f"{'='*70}\n")
    
    # Get context data
    buffer_size = context['ti'].xcom_pull(key='buffer_size', task_ids='check_buffer_size')
    
    output_dir = TRAINING_CONFIG['data_output_dir']
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Export baseline training data
    print(f"📊 Exporting baseline training data...")
    df_train = pd.read_sql("""
        SELECT "userId", "movieId", rating, timestamp
        FROM ratings
        WHERE data_split = 'train'
        ORDER BY timestamp
    """, engine)
    
    train_file = output_path / "ratings_train.parquet"
    df_train.to_parquet(train_file, index=False)
    print(f"✅ Saved: {train_file} ({len(df_train):,} ratings)")
    
    # Export buffer data (new data for retraining)
    print(f"\n📊 Exporting buffer data...")
    df_buffer = pd.read_sql("""
        SELECT "userId", "movieId", rating, timestamp
        FROM ratings_buffer
        ORDER BY timestamp
    """, engine)
    
    buffer_file = output_path / "ratings_buffer.parquet"
    df_buffer.to_parquet(buffer_file, index=False)
    print(f"✅ Saved: {buffer_file} ({len(df_buffer):,} ratings)")
    
    # Export test data
    print(f"\n📊 Exporting test data...")
    df_test = pd.read_sql("""
        SELECT "userId", "movieId", rating, timestamp
        FROM ratings
        WHERE data_split = 'test'
        ORDER BY timestamp
    """, engine)
    
    test_file = output_path / "ratings_test.parquet"
    df_test.to_parquet(test_file, index=False)
    print(f"✅ Saved: {test_file} ({len(df_test):,} ratings)")
    
    # Combine train + buffer for retraining
    print(f"\n📊 Creating combined dataset (train + buffer)...")
    df_combined = pd.concat([df_train, df_buffer], ignore_index=True)
    combined_file = output_path / "ratings_combined.parquet"
    df_combined.to_parquet(combined_file, index=False)
    print(f"✅ Saved: {combined_file} ({len(df_combined):,} ratings)")
    
    print(f"\n{'='*70}")
    print(f"✅ DATA EXPORT COMPLETE")
    print(f"{'='*70}")
    print(f"Location: {output_path.absolute()}")
    print(f"Files:")
    print(f"  • {train_file.name}: {len(df_train):,} ratings (baseline)")
    print(f"  • {buffer_file.name}: {len(df_buffer):,} ratings (new)")
    print(f"  • {test_file.name}: {len(df_test):,} ratings (validation)")
    print(f"  • {combined_file.name}: {len(df_combined):,} ratings (for retraining)")
    print()
    
    # Store file paths for next task
    data_files = {
        'train_file': str(train_file.absolute()),
        'buffer_file': str(buffer_file.absolute()),
        'test_file': str(test_file.absolute()),
        'combined_file': str(combined_file.absolute()),
        'train_size': len(df_train),
        'buffer_size': len(df_buffer),
        'combined_size': len(df_combined),
    }
    
    context['ti'].xcom_push(key='data_files', value=data_files)
    return data_files

def trigger_actual_retraining(**context):
    """
    Actually trigger model retraining by calling Julien's training script
    """
    print(f"\n{'='*70}")
    print(f"🚀 TRIGGERING ACTUAL MODEL RETRAINING")
    print(f"{'='*70}\n")
    
    # Get context data
    drift_alerts = context['ti'].xcom_pull(key='drift_alerts', task_ids='check_drift_alerts')
    buffer_size = context['ti'].xcom_pull(key='buffer_size', task_ids='check_buffer_size')
    data_files = context['ti'].xcom_pull(key='data_files', task_ids='export_training_data')
    
    # Safety check
    if not drift_alerts or len(drift_alerts) == 0:
        print(f"⚠️  No drift alerts found in context")
        drift_score = 0.0
        feature_name = "unknown"
    else:
        drift_score = drift_alerts[0]['drift_score']
        feature_name = drift_alerts[0]['feature_name']
    
    # Check if training script exists
    repo_path = Path(TRAINING_CONFIG['cinematch_root']) / 'movie-recommendation-mlflow'
    training_script = repo_path / TRAINING_CONFIG['training_script']
    
    if not training_script.exists():
        print(f"❌ Training script not found: {training_script}")
        print(f"   Please check TRAINING_CONFIG paths in DAG")
        raise FileNotFoundError(f"Training script not found: {training_script}")
    
    print(f"📂 Training script: {training_script}")
    print(f"📊 Training data: {data_files['combined_size']:,} ratings")
    print(f"🚨 Drift score: {drift_score:.4f}")
    print()
    
    # Prepare command
    cmd = [
        'python',
        str(training_script),
        '--data-path', data_files['combined_file'],
        '--test-path', data_files['test_file'],
        '--reason', 'drift_detected',
        '--drift-score', str(drift_score),
    ]
    
    print(f"🔧 Command:")
    print(f"   {' '.join(cmd)}\n")
    
    print(f"⏳ Starting training...\n")
    print(f"{'─'*70}\n")
    
    # Run training
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_path),
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        print(f"\n{'─'*70}\n")
        
        if result.returncode == 0:
            print(f"✅ TRAINING COMPLETED SUCCESSFULLY!")
            success = True
        else:
            print(f"❌ Training failed with exit code: {result.returncode}")
            success = False
            
    except Exception as e:
        print(f"❌ Error running training: {e}")
        success = False
    
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
            'decision': 'trigger_actual' if success else 'trigger_failed',
            'reason': 'drift_detected',
            'buffer_size': buffer_size,
            'drift_score': float(drift_score),
            'notes': f"Actual retraining {'successful' if success else 'failed'}. Feature: {feature_name}"
        })
    
    print(f"\n✅ Decision logged to retraining_decisions table")
    
    if success:
        print(f"\n{'='*70}")
        print(f"🎉 RETRAINING COMPLETE!")
        print(f"{'='*70}")
        print(f"Next steps:")
        print(f"  1. Check MLflow: {os.getenv('MLFLOW_TRACKING_URI', 'https://julienrouillard-mlflow-movie-recommandation.hf.space/')}")
        print(f"  2. Verify new model logged")
        print(f"  3. Check model metrics improved")
        print(f"  4. Update API if needed")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'='*70}")
        print(f"❌ RETRAINING FAILED!")
        print(f"{'='*70}")
        print(f"Check logs above for error details")
        print(f"{'='*70}\n")
        raise Exception("Model retraining failed")
    
    return success

def should_run_after_tests(**context):
    """
    Only run after-training tests if retraining completed successfully.
    """
    retrain_success = context['ti'].xcom_pull(task_ids='trigger_actual_retraining')
    return bool(retrain_success)

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
            if row['decision'] == 'trigger_actual':
                decision_icon = "🚀"
            elif row['decision'] == 'trigger_failed':
                decision_icon = "❌"
            else:
                decision_icon = "✅"
            print(f"   {decision_icon} {date_str} | {row['decision']:15s} | "
                  f"Buffer: {row['buffer_size']:,} | "
                  f"Drift: {row['drift_score']:.4f}" if row['drift_score'] else "Drift: N/A")
    else:
        print(f"   No previous decisions recorded")
    
    print(f"\n{'='*70}")
    if should_retrain:
        print(f"🎯 FINAL STATUS: RETRAINING TRIGGERED (ACTUAL)")
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

task_export_data = PythonOperator(
    task_id='export_training_data',
    python_callable=export_training_data,
    dag=dag,
)

task_trigger_training = PythonOperator(
    task_id='trigger_actual_retraining',
    python_callable=trigger_actual_retraining,
    dag=dag,
)

task_check_training_success = ShortCircuitOperator(
    task_id='check_training_success',
    python_callable=should_run_after_tests,
    dag=dag,
)

task_trigger_after_tests = TriggerDagRunOperator(
    task_id='trigger_after_training_tests',
    trigger_dag_id='after_training_tests_dag',
    wait_for_completion=False,
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
task_evaluate >> [task_export_data, task_no_retrain]
task_export_data >> task_trigger_training >> task_check_training_success >> task_trigger_after_tests
[task_trigger_after_tests, task_no_retrain] >> task_join >> task_summary
