"""
Buffer Ingestion DAG
Loads weekly rating batches from local files into Neon database
Simulates continuous data ingestion for MLOps pipeline
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
import os

# Default arguments
default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'buffer_ingestion_weekly',
    default_args=default_args,
    description='Ingest weekly rating batches into Neon',
    schedule_interval=None,  # Manual trigger (or @weekly for automation)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ingestion', 'cinematch', 'data-pipeline'],
)

def ingest_batch(batch_number: int, **context):
    """
    Ingest a specific batch into Neon database
    
    Args:
        batch_number: Which batch to ingest (1-5)
    """
    print(f"\n{'='*60}")
    print(f"📦 INGESTING BATCH {batch_number}")
    print(f"{'='*60}\n")
    
    # Get Neon connection
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    if not neon_conn:
        raise ValueError("NEON_CONNECTION_STRING not found in environment!")
    
    engine = create_engine(neon_conn)
    
    # Load batch file
    batch_path = f'/opt/airflow/data/prepared/buffer_batches/batch_w{batch_number}.parquet'
    
    print(f"📂 Loading batch from: {batch_path}")
    
    if not os.path.exists(batch_path):
        raise FileNotFoundError(f"Batch file not found: {batch_path}")
    
    df_batch = pd.read_parquet(batch_path)
    
    print(f"✅ Loaded {len(df_batch):,} ratings")
    print(f"   Columns: {df_batch.columns.tolist()}")
    
    # Add ingestion timestamp
    df_batch['ingested_at'] = pd.Timestamp.now()
    
    # Ensure batch_id is set
    if 'batch_id' not in df_batch.columns or df_batch['batch_id'].isna().all():
        df_batch['batch_id'] = f'batch_w{batch_number}'
    
    # Insert into Neon
    print(f"\n⬆️  Uploading to Neon ratings_buffer table...")
    
    try:
        df_batch.to_sql(
            'ratings_buffer',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=5000
        )
        print(f"✅ Successfully inserted {len(df_batch):,} rows into ratings_buffer")
    except Exception as e:
        print(f"❌ Failed to insert data: {str(e)}")
        raise
    
    # Log metadata
    print(f"\n📝 Logging ingestion metadata...")
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO ingestion_metadata 
                (batch_id, record_count, status, notes)
                VALUES (:batch_id, :count, :status, :notes)
                ON CONFLICT (batch_id) DO UPDATE
                SET record_count = :count,
                    status = :status,
                    ingestion_date = CURRENT_TIMESTAMP
            """), {
                'batch_id': f'batch_w{batch_number}',
                'count': len(df_batch),
                'status': 'completed',
                'notes': f'Weekly batch {batch_number} ingested successfully'
            })
            conn.commit()
        
        print(f"✅ Metadata logged successfully")
    except Exception as e:
        print(f"⚠️  Warning: Failed to log metadata: {str(e)}")
        # Don't fail the task if metadata logging fails
    
    # Verify insertion
    print(f"\n🔍 Verifying data in Neon...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM ratings_buffer 
            WHERE batch_id = :batch_id
        """), {'batch_id': f'batch_w{batch_number}'})
        
        count_in_db = result.fetchone()[0]
        print(f"✅ Verified: {count_in_db:,} rows in database for batch_w{batch_number}")
    
    print(f"\n{'='*60}")
    print(f"🎉 BATCH {batch_number} INGESTION COMPLETE")
    print(f"{'='*60}\n")
    
    return {
        'batch_number': batch_number,
        'records_ingested': len(df_batch),
        'status': 'success'
    }

def check_buffer_status(**context):
    """
    Check overall status of buffer ingestion
    """
    print(f"\n{'='*60}")
    print(f"📊 BUFFER INGESTION STATUS")
    print(f"{'='*60}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Check total records in buffer
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT batch_id) as num_batches
            FROM ratings_buffer
        """))
        row = result.fetchone()
        total_records = row[0]
        num_batches = row[1]
    
    print(f"📈 Total records in buffer: {total_records:,}")
    print(f"📦 Number of batches: {num_batches}")
    
    # Check metadata
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT batch_id, record_count, status, ingestion_date
            FROM ingestion_metadata
            ORDER BY ingestion_date DESC
        """))
        
        print(f"\n📋 Ingestion History:")
        for row in result:
            print(f"   {row[0]}: {row[1]:,} records - {row[2]} - {row[3]}")
    
    print(f"\n{'='*60}\n")
    
    return {
        'total_records': total_records,
        'num_batches': num_batches
    }


def get_next_batch_to_ingest(**context):
    """
    Determine which batch should be ingested next
    Returns the batch number (1-8) or None if all batches are ingested
    """
    print(f"\n{'='*60}")
    print(f"🔍 DETECTING NEXT BATCH TO INGEST")
    print(f"{'='*60}\n")
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    engine = create_engine(neon_conn)
    
    # Get all ingested batches
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT batch_id
            FROM ratings_buffer
            ORDER BY batch_id
        """))
        
        ingested_batches = [row[0] for row in result]
    
    print(f"📦 Already ingested batches: {ingested_batches}")
    
    # Find next batch to ingest (1-8)
    for i in range(1, 9):  # Batches 1 to 8
        batch_id = f'batch_w{i}'
        if batch_id not in ingested_batches:
            print(f"✅ Next batch to ingest: {i}")
            print(f"{'='*60}\n")
            context['ti'].xcom_push(key='next_batch', value=i)
            return i
    
    # All batches ingested
    print(f"🎉 All batches (1-8) have been ingested!")
    print(f"{'='*60}\n")
    context['ti'].xcom_push(key='next_batch', value=None)
    return None


# Task 1: Detect next batch to ingest
detect_batch_task = PythonOperator(
    task_id='detect_next_batch',
    python_callable=get_next_batch_to_ingest,
    dag=dag,
)

# Task 2: Ingest the detected batch (reads batch number from XCom)
def ingest_next_batch(**context):
    """Ingest the next batch detected by detect_next_batch"""
    batch_number = context['ti'].xcom_pull(key='next_batch', task_ids='detect_next_batch')
    
    if batch_number is None:
        print("🎉 All batches already ingested. Nothing to do!")
        return None
    
    # Call the original ingest_batch function
    return ingest_batch(batch_number, **context)

ingest_task = PythonOperator(
    task_id='ingest_detected_batch',
    python_callable=ingest_next_batch,
    dag=dag,
)

# Task 3: Trigger batch predictions with proper conf
def trigger_batch_predictions_task(**context):
    """Trigger batch_predictions DAG with the correct batch_id"""
    from airflow.api.common.trigger_dag import trigger_dag
    
    batch_number = context['ti'].xcom_pull(key='next_batch', task_ids='detect_next_batch')
    
    if batch_number is None:
        print("⏭️  No batch to predict. Skipping.")
        return None
    
    batch_id = f'batch_w{batch_number}'
    print(f"🚀 Triggering batch_predictions with batch_id={batch_id}")
    
    trigger_dag(
        dag_id='batch_predictions',
        conf={'batch_id': batch_id},
        execution_date=None,
        replace_microseconds=False
    )
    
    print(f"✅ Successfully triggered batch_predictions")
    return batch_id

trigger_task = PythonOperator(
    task_id='trigger_batch_predictions',
    python_callable=trigger_batch_predictions_task,
    dag=dag,
)


# Task 4: Status check
status_task = PythonOperator(
    task_id='check_buffer_status',
    python_callable=check_buffer_status,
    dag=dag,
)

# Dependencies
detect_batch_task >> ingest_task >> trigger_task >> status_task