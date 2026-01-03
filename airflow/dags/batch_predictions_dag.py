"""
Batch Predictions DAG
Makes predictions via API for a specific batch in ratings_buffer
Stores predicted_rating, calculates performance metrics
ALWAYS triggers drift monitoring (data drift check)
CONDITIONALLY triggers retraining (if model performance degraded)
Triggered by the ingestion DAG with batch_id in configuration
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
import pandas as pd
import requests
from sqlalchemy import create_engine, text
import os
from time import sleep

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════ CONFIGURATION ════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

# Default arguments
default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# API Configuration
API_URL = "https://julienrouillard-movie-recommendation-api.hf.space"
BATCH_SIZE = 100

# Performance thresholds (for model drift detection)
EXPECTED_MAE = 0.79
EXPECTED_RMSE = 1.02
DEGRADATION_THRESHOLD = 0.1  # Trigger retraining if performance degrades by 10%

# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════ DAG ══════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

dag = DAG(
    'batch_predictions',
    default_args=default_args,
    description='Predict ratings, detect model drift, trigger retraining if needed',
    schedule_interval=None,  # Triggered by ingestion DAG with batch_id
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['predictions', 'cinematch', 'api', 'batch', 'model-monitoring'],
)

# ══════════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════ TASK FUNCTIONS ══════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

def ensure_predicted_rating_column(**context):
    """
    Add predicted_rating column to ratings_buffer if it doesn't exist
    """
    print(f"\n{'='*70}")
    print(f"🔧 ENSURING PREDICTED_RATING COLUMN EXISTS")
    print(f"{'='*70}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    with engine.begin() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ratings_buffer' 
            AND column_name = 'predicted_rating'
        """))
        
        if result.fetchone() is None:
            print("📝 Column predicted_rating does not exist - creating it...")
            conn.execute(text("""
                ALTER TABLE ratings_buffer 
                ADD COLUMN predicted_rating FLOAT
            """))
            print("✅ Column predicted_rating created successfully")
        else:
            print("✅ Column predicted_rating already exists")
    
    print(f"\n{'='*70}\n")


def load_buffer_data(**context):
    """
    Load records from ratings_buffer for the specific batch_id
    """
    print(f"\n{'='*70}")
    print(f"📥 LOADING DATA FROM RATINGS_BUFFER")
    print(f"{'='*70}\n")
    
    # Get batch_id from DAG run configuration
    batch_id = context['dag_run'].conf.get('batch_id') if context['dag_run'].conf else None
    
    if batch_id is None:
        print("❌ ERROR: No batch_id provided in DAG run configuration")
        print("   This DAG must be triggered with: {'batch_id': 'your_batch_id'}")
        raise ValueError("batch_id is required in DAG run configuration")
    
    print(f"🎯 Target batch_id: {batch_id}")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Load records for this specific batch only
    print(f"📊 Querying ratings_buffer for batch {batch_id}...")
    df = pd.read_sql("""
        SELECT userId, movieId, rating, batch_id, timestamp
        FROM ratings_buffer
        WHERE batch_id = :batch_id
        ORDER BY timestamp
    """, engine, params={'batch_id': batch_id})
    
    if len(df) == 0:
        print(f"⚠️  No data found for batch_id '{batch_id}'")
        print(f"   Check if this batch exists in ratings_buffer")
        context['ti'].xcom_push(key='data_count', value=0)
        context['ti'].xcom_push(key='batch_id', value=batch_id)
        return None
    
    print(f"✅ Loaded {len(df):,} records for batch '{batch_id}'")
    print(f"   Users: {df['userId'].nunique():,} unique")
    print(f"   Movies: {df['movieId'].nunique():,} unique")
    print(f"   Rating range: [{df['rating'].min():.1f}, {df['rating'].max():.1f}]")
    print(f"   Mean rating: {df['rating'].mean():.2f}")
    
    # Store data and batch_id for next tasks
    context['ti'].xcom_push(key='data_count', value=len(df))
    context['ti'].xcom_push(key='batch_id', value=batch_id)
    context['ti'].xcom_push(key='buffer_data', value=df.to_dict('records'))
    
    print(f"\n✅ Data loaded and ready for predictions\n")
    
    return len(df)


def make_batch_predictions(**context):
    """
    Call API to predict ratings for all records in the batch
    """
    print(f"\n{'='*70}")
    print(f"🤖 MAKING BATCH PREDICTIONS VIA API")
    print(f"{'='*70}\n")
    
    data_count = context['ti'].xcom_pull(key='data_count', task_ids='load_data')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    if data_count == 0:
        print(f"⚠️  No data to predict for batch '{batch_id}' - skipping")
        return None
    
    buffer_data = context['ti'].xcom_pull(key='buffer_data', task_ids='load_data')
    df = pd.DataFrame(buffer_data)
    
    print(f"📊 Starting predictions for batch '{batch_id}'")
    print(f"   Records: {len(df):,}")
    print(f"   API URL: {API_URL}")
    print(f"   Batch size: {BATCH_SIZE}")
    
    predictions = []
    total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} records)...")
        
        batch_success = 0
        batch_failures = 0
        
        for idx, row in batch.iterrows():
            try:
                # Call API
                response = requests.post(
                    f"{API_URL}/predict",
                    json={
                        "user_id": int(row['userId']),
                        "movie_id": int(row['movieId'])
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    predicted_rating = response.json()['rating']
                    predictions.append({
                        'userId': row['userId'],
                        'movieId': row['movieId'],
                        'predicted_rating': predicted_rating,
                        'actual_rating': row['rating']
                    })
                    batch_success += 1
                else:
                    print(f"   ⚠️  API error ({response.status_code}) for user {row['userId']}, movie {row['movieId']}")
                    predictions.append({
                        'userId': row['userId'],
                        'movieId': row['movieId'],
                        'predicted_rating': None,
                        'actual_rating': row['rating']
                    })
                    batch_failures += 1
                
                
            except requests.exceptions.Timeout:
                print(f"   ⏱️  Timeout for user {row['userId']}, movie {row['movieId']}")
                predictions.append({
                    'userId': row['userId'],
                    'movieId': row['movieId'],
                    'predicted_rating': None,
                    'actual_rating': row['rating']
                })
                batch_failures += 1
                
            except Exception as e:
                print(f"   ❌ Error for user {row['userId']}, movie {row['movieId']}: {e}")
                predictions.append({
                    'userId': row['userId'],
                    'movieId': row['movieId'],
                    'predicted_rating': None,
                    'actual_rating': row['rating']
                })
                batch_failures += 1
        
        print(f"   ✅ Batch {batch_num} completed - Success: {batch_success}, Failed: {batch_failures}")
    
    # Calculate success rate
    successful = len([p for p in predictions if p['predicted_rating'] is not None])
    success_rate = (successful / len(predictions)) * 100 if len(predictions) > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"📊 PREDICTION SUMMARY FOR BATCH '{batch_id}'")
    print(f"{'='*70}")
    print(f"   Total requests: {len(predictions):,}")
    print(f"   Successful: {successful:,}")
    print(f"   Failed: {len(predictions) - successful:,}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"{'='*70}\n")
    
    # Store predictions
    context['ti'].xcom_push(key='predictions', value=predictions)
    context['ti'].xcom_push(key='success_count', value=successful)
    
    print(f"✅ Batch predictions completed\n")
    
    return predictions


def update_buffer_with_predictions(**context):
    """
    Update ratings_buffer with predicted ratings for the specific batch
    """
    print(f"\n{'='*70}")
    print(f"💾 UPDATING RATINGS_BUFFER WITH PREDICTIONS")
    print(f"{'='*70}\n")
    
    predictions = context['ti'].xcom_pull(key='predictions', task_ids='make_predictions')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    if predictions is None or len(predictions) == 0:
        print(f"⚠️  No predictions to update for batch '{batch_id}'")
        return 0
    
    print(f"🎯 Updating batch: '{batch_id}'")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    print(f"📝 Updating {len(predictions):,} records...")
    
    updated = 0
    skipped = 0
    failed = 0
    
    with engine.begin() as conn:
        for pred in predictions:
            if pred['predicted_rating'] is not None:
                try:
                    result = conn.execute(text("""
                        UPDATE ratings_buffer
                        SET predicted_rating = :pred_rating
                        WHERE userId = :user_id 
                        AND movieId = :movie_id 
                        AND batch_id = :batch_id
                    """), {
                        'pred_rating': pred['predicted_rating'],
                        'user_id': pred['userId'],
                        'movie_id': pred['movieId'],
                        'batch_id': batch_id
                    })
                    
                    if result.rowcount > 0:
                        updated += 1
                    else:
                        skipped += 1
                        
                except Exception as e:
                    print(f"   ❌ Failed to update user {pred['userId']}, movie {pred['movieId']}: {e}")
                    failed += 1
            else:
                skipped += 1
    
    print(f"\n{'='*70}")
    print(f"✅ DATABASE UPDATE COMPLETED")
    print(f"{'='*70}")
    print(f"   Updated successfully: {updated:,}")
    print(f"   Skipped (null predictions): {skipped:,}")
    print(f"   Failed: {failed:,}")
    print(f"{'='*70}\n")
    
    return updated


def calculate_prediction_metrics(**context):
    """
    Calculate performance metrics (MAE, RMSE) to detect model drift
    """
    print(f"\n{'='*70}")
    print(f"📊 CALCULATING PREDICTION METRICS (MODEL DRIFT DETECTION)")
    print(f"{'='*70}\n")
    
    predictions = context['ti'].xcom_pull(key='predictions', task_ids='make_predictions')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    if predictions is None or len(predictions) == 0:
        print(f"⚠️  No predictions to evaluate for batch '{batch_id}'")
        context['ti'].xcom_push(key='model_drift_detected', value=False)
        return None
    
    # Filter successful predictions
    valid_preds = [p for p in predictions if p['predicted_rating'] is not None]
    
    if len(valid_preds) == 0:
        print(f"⚠️  No valid predictions to evaluate for batch '{batch_id}'")
        context['ti'].xcom_push(key='model_drift_detected', value=False)
        return None
    
    print(f"📈 Evaluating {len(valid_preds):,} predictions for batch '{batch_id}'")
    
    # Calculate metrics
    errors = [abs(p['predicted_rating'] - p['actual_rating']) for p in valid_preds]
    squared_errors = [(p['predicted_rating'] - p['actual_rating'])**2 for p in valid_preds]
    
    mae = sum(errors) / len(errors)
    rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5
    
    # Additional statistics
    mean_actual = sum([p['actual_rating'] for p in valid_preds]) / len(valid_preds)
    mean_predicted = sum([p['predicted_rating'] for p in valid_preds]) / len(valid_preds)
    
    metrics = {
        'batch_id': batch_id,
        'mae': mae,
        'rmse': rmse,
        'n_predictions': len(valid_preds),
        'mean_actual': mean_actual,
        'mean_predicted': mean_predicted
    }
    
    print(f"\n{'='*70}")
    print(f"📈 PERFORMANCE METRICS - BATCH '{batch_id}'")
    print(f"{'='*70}")
    print(f"   MAE (Mean Absolute Error): {mae:.4f}")
    print(f"   RMSE (Root Mean Squared Error): {rmse:.4f}")
    print(f"   Number of predictions: {len(valid_preds):,}")
    print(f"   Mean actual rating: {mean_actual:.3f}")
    print(f"   Mean predicted rating: {mean_predicted:.3f}")
    print(f"{'='*70}")
    
    # Compare with baseline
    print(f"\n💡 Model Baseline Comparison:")
    print(f"   Expected MAE: {EXPECTED_MAE:.4f}")
    print(f"   Expected RMSE: {EXPECTED_RMSE:.4f}")
    print(f"   Degradation threshold: {DEGRADATION_THRESHOLD*100:.0f}%")
    
    mae_change = ((mae / EXPECTED_MAE) - 1) * 100
    rmse_change = ((rmse / EXPECTED_RMSE) - 1) * 100
    
    print(f"\n   Current vs Baseline:")
    print(f"   MAE change: {mae_change:+.1f}%")
    print(f"   RMSE change: {rmse_change:+.1f}%")
    
    # Determine if model drift detected
    mae_degraded = mae > EXPECTED_MAE * (1 + DEGRADATION_THRESHOLD)
    rmse_degraded = rmse > EXPECTED_RMSE * (1 + DEGRADATION_THRESHOLD)
    model_drift_detected = mae_degraded or rmse_degraded
    
    print(f"\n{'='*70}")
    print(f"🎯 MODEL DRIFT DETECTION RESULT")
    print(f"{'='*70}")
    
    if model_drift_detected:
        print(f"   🚨 MODEL DRIFT DETECTED!")
        print(f"   ⚠️  Model performance has degraded significantly")
        
        if mae_degraded:
            print(f"   - MAE degraded by {mae_change:.1f}% (threshold: {DEGRADATION_THRESHOLD*100:.0f}%)")
        if rmse_degraded:
            print(f"   - RMSE degraded by {rmse_change:.1f}% (threshold: {DEGRADATION_THRESHOLD*100:.0f}%)")
        
        print(f"\n   💡 Action: RETRAINING DAG WILL BE TRIGGERED")
    else:
        print(f"   ✅ NO MODEL DRIFT DETECTED")
        print(f"   📊 Model performance is stable")
        print(f"   💡 Action: No retraining needed")
    
    print(f"{'='*70}\n")
    
    # Store metrics and drift status
    context['ti'].xcom_push(key='metrics', value=metrics)
    context['ti'].xcom_push(key='model_drift_detected', value=model_drift_detected)
    
    return metrics


def check_and_trigger_retraining(**context):
    """
    Check if model drift was detected and trigger retraining if needed
    """
    print(f"\n{'='*70}")
    print(f"🔍 CHECKING IF RETRAINING NEEDED")
    print(f"{'='*70}\n")
    
    model_drift_detected = context['ti'].xcom_pull(key='model_drift_detected', task_ids='calculate_metrics')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    if model_drift_detected:
        print(f"🚨 Model drift detected for batch '{batch_id}'")
        print(f"   Triggering retraining DAG...")
        return 'trigger_retraining'
    else:
        print(f"✅ No model drift detected for batch '{batch_id}'")
        print(f"   Skipping retraining")
        return 'skip_retraining'


def skip_retraining(**context):
    """
    Dummy task when retraining is not needed
    """
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    print(f"\n✅ Retraining skipped for batch '{batch_id}' - model performance is stable\n")


# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════ TASKS ════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

task_ensure_column = PythonOperator(
    task_id='ensure_column',
    python_callable=ensure_predicted_rating_column,
    dag=dag,
)

task_load_data = PythonOperator(
    task_id='load_data',
    python_callable=load_buffer_data,
    dag=dag,
)

task_make_predictions = PythonOperator(
    task_id='make_predictions',
    python_callable=make_batch_predictions,
    dag=dag,
)

task_update_buffer = PythonOperator(
    task_id='update_buffer',
    python_callable=update_buffer_with_predictions,
    dag=dag,
)

task_calculate_metrics = PythonOperator(
    task_id='calculate_metrics',
    python_callable=calculate_prediction_metrics,
    dag=dag,
)

# Conditional trigger for retraining
task_trigger_retraining = TriggerDagRunOperator(
    task_id='trigger_retraining',
    trigger_dag_id='trigger_retraining_dag',
    wait_for_completion=False,
    dag=dag,
)

task_skip_retraining = PythonOperator(
    task_id='skip_retraining',
    python_callable=skip_retraining,
    dag=dag,
)

# ALWAYS trigger drift monitoring (data drift check)
task_trigger_drift = TriggerDagRunOperator(
    task_id='trigger_drift_monitoring',
    trigger_dag_id='drift_monitoring',
    wait_for_completion=False,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ══════════════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════ TASK DEPENDENCIES ═════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

# Main pipeline
task_ensure_column >> task_load_data >> task_make_predictions >> task_update_buffer >> task_calculate_metrics

# After metrics: check if retraining needed
task_calculate_metrics >> [task_trigger_retraining, task_skip_retraining]

# Always trigger drift monitoring after everything
[task_trigger_retraining, task_skip_retraining] >> task_trigger_drift