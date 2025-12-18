"""
Drift Monitoring DAG
Detects data distribution changes between baseline (training data) and new data (buffer)
Logs alerts when drift is detected to trigger retraining decisions
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from scipy.stats import ks_2samp
import os

# Default arguments
default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

# Define the DAG
dag = DAG(
    'drift_monitoring',
    default_args=default_args,
    description='Monitor data drift and alert when retraining is needed',
    schedule_interval='@daily',  # Run daily (or change to None for manual)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['monitoring', 'cinematch', 'drift-detection'],
)

# Drift thresholds (configurable)
DRIFT_THRESHOLDS = {
    'ks_statistic': 0.05,      # Kolmogorov-Smirnov test threshold
    'mean_change': 0.10,        # 10% change in mean rating
    'std_change': 0.15,         # 15% change in standard deviation
    'count_threshold': 10000,   # Minimum records in buffer to check drift
}

def load_baseline_statistics(**context):
    """
    Load and calculate statistics from baseline training data
    """
    print(f"\n{'='*70}")
    print(f"📊 LOADING BASELINE STATISTICS")
    print(f"{'='*70}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Load baseline ratings (training data)
    print("📥 Querying baseline data from ratings table...")
    df_baseline = pd.read_sql("""
        SELECT rating, timestamp
        FROM ratings
        WHERE data_split = 'train'
    """, engine)
    
    print(f"✅ Loaded {len(df_baseline):,} baseline ratings")
    
    # Calculate statistics
    stats = {
        'count': len(df_baseline),
        'mean': df_baseline['rating'].mean(),
        'std': df_baseline['rating'].std(),
        'min': df_baseline['rating'].min(),
        'max': df_baseline['rating'].max(),
        'median': df_baseline['rating'].median(),
    }
    
    # Rating distribution
    distribution = df_baseline['rating'].value_counts(normalize=True).sort_index()
    stats['distribution'] = distribution.to_dict()
    
    print(f"\n📈 Baseline Statistics:")
    print(f"   Count: {stats['count']:,}")
    print(f"   Mean: {stats['mean']:.3f}")
    print(f"   Std: {stats['std']:.3f}")
    print(f"   Median: {stats['median']:.3f}")
    print(f"   Range: [{stats['min']:.1f}, {stats['max']:.1f}]")
    print(f"\n   Rating Distribution:")
    for rating, pct in sorted(stats['distribution'].items()):
        print(f"      {rating:.1f} stars: {pct*100:.1f}%")
    
    # Store for next task
    context['ti'].xcom_push(key='baseline_stats', value=stats)
    context['ti'].xcom_push(key='baseline_ratings', value=df_baseline['rating'].tolist())
    
    print(f"\n✅ Baseline statistics calculated and stored\n")
    
    return stats

def load_new_data_statistics(**context):
    """
    Load and calculate statistics from new buffer data
    """
    print(f"\n{'='*70}")
    print(f"📦 LOADING NEW DATA STATISTICS")
    print(f"{'='*70}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Load buffer ratings (new data)
    print("📥 Querying new data from ratings_buffer...")
    df_new = pd.read_sql("""
        SELECT rating, timestamp, batch_id
        FROM ratings_buffer
        ORDER BY timestamp
    """, engine)
    
    if len(df_new) == 0:
        print("⚠️  No data in ratings_buffer - skipping drift detection")
        context['ti'].xcom_push(key='new_stats', value=None)
        return None
    
    print(f"✅ Loaded {len(df_new):,} new ratings")
    print(f"   Batches: {df_new['batch_id'].unique().tolist()}")
    
    # Calculate statistics
    stats = {
        'count': len(df_new),
        'mean': df_new['rating'].mean(),
        'std': df_new['rating'].std(),
        'min': df_new['rating'].min(),
        'max': df_new['rating'].max(),
        'median': df_new['rating'].median(),
    }
    
    # Rating distribution
    distribution = df_new['rating'].value_counts(normalize=True).sort_index()
    stats['distribution'] = distribution.to_dict()
    
    print(f"\n📈 New Data Statistics:")
    print(f"   Count: {stats['count']:,}")
    print(f"   Mean: {stats['mean']:.3f}")
    print(f"   Std: {stats['std']:.3f}")
    print(f"   Median: {stats['median']:.3f}")
    print(f"   Range: [{stats['min']:.1f}, {stats['max']:.1f}]")
    print(f"\n   Rating Distribution:")
    for rating, pct in sorted(stats['distribution'].items()):
        print(f"      {rating:.1f} stars: {pct*100:.1f}%")
    
    # Store for next task
    context['ti'].xcom_push(key='new_stats', value=stats)
    context['ti'].xcom_push(key='new_ratings', value=df_new['rating'].tolist())
    
    print(f"\n✅ New data statistics calculated and stored\n")
    
    return stats

def calculate_drift_scores(**context):
    """
    Calculate drift scores using multiple statistical tests
    """
    print(f"\n{'='*70}")
    print(f"🔍 CALCULATING DRIFT SCORES")
    print(f"{'='*70}\n")
    
    # Retrieve statistics from previous tasks
    baseline_stats = context['ti'].xcom_pull(key='baseline_stats', task_ids='load_baseline')
    new_stats = context['ti'].xcom_pull(key='new_stats', task_ids='load_new_data')
    
    if new_stats is None:
        print("⚠️  No new data - skipping drift calculation")
        return None
    
    # Check if we have enough data
    if new_stats['count'] < DRIFT_THRESHOLDS['count_threshold']:
        print(f"⚠️  Insufficient new data ({new_stats['count']:,} < {DRIFT_THRESHOLDS['count_threshold']:,})")
        print(f"   Waiting for more data before drift detection...")
        return None
    
    drift_results = {}
    
    # 1. KOLMOGOROV-SMIRNOV TEST (distribution comparison)
    print("📊 Test 1: Kolmogorov-Smirnov Test (Distribution Comparison)")
    baseline_ratings = context['ti'].xcom_pull(key='baseline_ratings', task_ids='load_baseline')
    new_ratings = context['ti'].xcom_pull(key='new_ratings', task_ids='load_new_data')
    
    ks_statistic, ks_pvalue = ks_2samp(baseline_ratings, new_ratings)
    drift_results['ks_statistic'] = float(ks_statistic)
    drift_results['ks_pvalue'] = float(ks_pvalue)
    drift_results['ks_drift_detected'] = bool(ks_statistic > DRIFT_THRESHOLDS['ks_statistic'])
    
    print(f"   KS Statistic: {ks_statistic:.4f}")
    print(f"   P-value: {ks_pvalue:.4f}")
    print(f"   Threshold: {DRIFT_THRESHOLDS['ks_statistic']}")
    print(f"   Result: {'🚨 DRIFT DETECTED' if drift_results['ks_drift_detected'] else '✅ No drift'}")
    
    # 2. MEAN CHANGE (average rating shift)
    print(f"\n📊 Test 2: Mean Rating Change")
    mean_change = abs(new_stats['mean'] - baseline_stats['mean']) / baseline_stats['mean']
    drift_results['mean_baseline'] = float(baseline_stats['mean'])
    drift_results['mean_new'] = float(new_stats['mean'])
    drift_results['mean_change_pct'] = float(mean_change * 100)
    drift_results['mean_drift_detected'] = bool(mean_change > DRIFT_THRESHOLDS['mean_change'])
    
    print(f"   Baseline mean: {baseline_stats['mean']:.3f}")
    print(f"   New mean: {new_stats['mean']:.3f}")
    print(f"   Change: {mean_change*100:.1f}%")
    print(f"   Threshold: {DRIFT_THRESHOLDS['mean_change']*100:.0f}%")
    print(f"   Result: {'🚨 DRIFT DETECTED' if drift_results['mean_drift_detected'] else '✅ No drift'}")
    
    # 3. STANDARD DEVIATION CHANGE (variance shift)
    print(f"\n📊 Test 3: Standard Deviation Change")
    std_change = abs(new_stats['std'] - baseline_stats['std']) / baseline_stats['std']
    drift_results['std_baseline'] = float(baseline_stats['std'])
    drift_results['std_new'] = float(new_stats['std'])
    drift_results['std_change_pct'] = float(std_change * 100)
    drift_results['std_drift_detected'] = bool(std_change > DRIFT_THRESHOLDS['std_change'])
    
    print(f"   Baseline std: {baseline_stats['std']:.3f}")
    print(f"   New std: {new_stats['std']:.3f}")
    print(f"   Change: {std_change*100:.1f}%")
    print(f"   Threshold: {DRIFT_THRESHOLDS['std_change']*100:.0f}%")
    print(f"   Result: {'🚨 DRIFT DETECTED' if drift_results['std_drift_detected'] else '✅ No drift'}")
    
    # 4. OVERALL DRIFT DECISION
    print(f"\n{'='*70}")
    print(f"🎯 OVERALL DRIFT ASSESSMENT")
    print(f"{'='*70}\n")
    
    drift_detected = (
        drift_results['ks_drift_detected'] or 
        drift_results['mean_drift_detected'] or 
        drift_results['std_drift_detected']
    )
    
    drift_results['overall_drift_detected'] = drift_detected
    drift_results['data_count'] = new_stats['count']
    
    if drift_detected:
        print("   🚨 DRIFT DETECTED!")
        print("   ⚠️  Data distribution has changed significantly")
        print("   💡 Recommendation: RETRAIN MODEL with new data")
        
        triggered_by = []
        if drift_results['ks_drift_detected']:
            triggered_by.append("Distribution shift")
        if drift_results['mean_drift_detected']:
            triggered_by.append("Mean change")
        if drift_results['std_drift_detected']:
            triggered_by.append("Variance change")
        
        print(f"   📋 Triggered by: {', '.join(triggered_by)}")
    else:
        print("   ✅ NO SIGNIFICANT DRIFT DETECTED")
        print("   📊 Data distribution is stable")
        print("   💡 Recommendation: Continue monitoring")
    
    print(f"\n{'='*70}\n")
    
    # Store results
    context['ti'].xcom_push(key='drift_results', value=drift_results)
    
    return drift_results

def log_drift_alerts(**context):
    """
    Log drift detection results to Neon database
    """
    print(f"\n{'='*70}")
    print(f"📝 LOGGING DRIFT ALERTS TO DATABASE")
    print(f"{'='*70}\n")
    
    drift_results = context['ti'].xcom_pull(key='drift_results', task_ids='calculate_drift')
    
    if drift_results is None:
        print("⚠️  No drift results to log (insufficient data)")
        return
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Log KS test result
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO drift_alerts 
            (feature_name, drift_score, threshold, alert_triggered, notes)
            VALUES (:feature, :score, :threshold, :triggered, :notes)
        """), {
            'feature': 'rating_distribution_ks',
            'score': drift_results['ks_statistic'],
            'threshold': DRIFT_THRESHOLDS['ks_statistic'],
            'triggered': drift_results['ks_drift_detected'],
            'notes': f"KS test p-value: {drift_results['ks_pvalue']:.4f}"
        })
    
    print(f"✅ Logged KS test result")
    
    # Log mean change
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO drift_alerts 
            (feature_name, drift_score, threshold, alert_triggered, notes)
            VALUES (:feature, :score, :threshold, :triggered, :notes)
        """), {
            'feature': 'rating_mean',
            'score': drift_results['mean_change_pct'] / 100,
            'threshold': DRIFT_THRESHOLDS['mean_change'],
            'triggered': drift_results['mean_drift_detected'],
            'notes': f"Baseline: {drift_results['mean_baseline']:.3f}, New: {drift_results['mean_new']:.3f}"
        })
    
    print(f"✅ Logged mean change result")
    
    # Log std change
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO drift_alerts 
            (feature_name, drift_score, threshold, alert_triggered, notes)
            VALUES (:feature, :score, :threshold, :triggered, :notes)
        """), {
            'feature': 'rating_std',
            'score': drift_results['std_change_pct'] / 100,
            'threshold': DRIFT_THRESHOLDS['std_change'],
            'triggered': drift_results['std_drift_detected'],
            'notes': f"Baseline: {drift_results['std_baseline']:.3f}, New: {drift_results['std_new']:.3f}"
        })
    
    print(f"✅ Logged std change result")
    
    print(f"\n✅ All drift alerts logged to database")
    print(f"   Check drift_alerts table in Neon for details\n")

def generate_drift_report(**context):
    """
    Generate final drift monitoring report
    """
    print(f"\n{'='*70}")
    print(f"📋 DRIFT MONITORING REPORT")
    print(f"{'='*70}\n")
    
    drift_results = context['ti'].xcom_pull(key='drift_results', task_ids='calculate_drift')
    
    if drift_results is None:
        print("⚠️  No drift analysis performed (insufficient data)")
        print("   Waiting for more buffer data...")
        return
    
    baseline_stats = context['ti'].xcom_pull(key='baseline_stats', task_ids='load_baseline')
    new_stats = context['ti'].xcom_pull(key='new_stats', task_ids='load_new_data')
    
    print(f"📊 Data Summary:")
    print(f"   Baseline data: {baseline_stats['count']:,} ratings")
    print(f"   New data: {new_stats['count']:,} ratings")
    
    print(f"\n🔍 Drift Tests:")
    print(f"   1. Distribution (KS test): {'🚨 DRIFT' if drift_results['ks_drift_detected'] else '✅ OK'}")
    print(f"   2. Mean change: {'🚨 DRIFT' if drift_results['mean_drift_detected'] else '✅ OK'}")
    print(f"   3. Std change: {'🚨 DRIFT' if drift_results['std_drift_detected'] else '✅ OK'}")
    
    print(f"\n{'='*70}")
    if drift_results['overall_drift_detected']:
        print(f"🚨 FINAL DECISION: DRIFT DETECTED - RETRAINING RECOMMENDED")
    else:
        print(f"✅ FINAL DECISION: NO DRIFT - CONTINUE MONITORING")
    print(f"{'='*70}\n")
    
    return drift_results

# Define tasks
task_load_baseline = PythonOperator(
    task_id='load_baseline',
    python_callable=load_baseline_statistics,
    dag=dag,
)

task_load_new_data = PythonOperator(
    task_id='load_new_data',
    python_callable=load_new_data_statistics,
    dag=dag,
)

task_calculate_drift = PythonOperator(
    task_id='calculate_drift',
    python_callable=calculate_drift_scores,
    dag=dag,
)

task_log_alerts = PythonOperator(
    task_id='log_alerts',
    python_callable=log_drift_alerts,
    dag=dag,
)

task_generate_report = PythonOperator(
    task_id='generate_report',
    python_callable=generate_drift_report,
    dag=dag,
)

# Set dependencies
[task_load_baseline, task_load_new_data] >> task_calculate_drift >> task_log_alerts >> task_generate_report
