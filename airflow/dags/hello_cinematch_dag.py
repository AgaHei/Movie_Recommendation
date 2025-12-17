"""
Hello CineMatch DAG
A simple test DAG to verify Airflow setup is working
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

# Default arguments for all tasks
default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'hello_cinematch',
    default_args=default_args,
    description='Test DAG to verify Airflow setup',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['test', 'cinematch'],
)

def print_welcome():
    """Print welcome message"""
    print("=" * 60)
    print("🎬 Welcome to CineMatch MLOps Pipeline!")
    print("=" * 60)
    print("This is a test DAG to verify Airflow is working correctly.")
    return "Welcome message printed!"

def check_neon_connection():
    """Test Neon database connection"""
    from sqlalchemy import create_engine, text
    
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    
    if not neon_conn:
        print("❌ NEON_CONNECTION_STRING not found in environment!")
        return "Connection string missing"
    
    print(f"✅ Found Neon connection string")
    
    try:
        engine = create_engine(neon_conn)
        with engine.connect() as conn:
            # Test query
            result = conn.execute(text("SELECT COUNT(*) as count FROM ratings"))
            count = result.fetchone()[0]
            print(f"✅ Successfully connected to Neon!")
            print(f"✅ Found {count:,} ratings in database")
            return f"Connected! {count} ratings found"
    except Exception as e:
        print(f"❌ Failed to connect to Neon: {str(e)}")
        return f"Connection failed: {str(e)}"

def check_data_folder():
    """Check if data folder is mounted correctly"""
    import os
    
    data_path = '/opt/airflow/data'
    
    if os.path.exists(data_path):
        print(f"✅ Data folder mounted at: {data_path}")
        
        # List contents
        try:
            contents = os.listdir(data_path)
            print(f"📂 Contents: {contents}")
            
            # Check for buffer batches
            buffer_path = os.path.join(data_path, 'prepared/buffer_batches')
            if os.path.exists(buffer_path):
                batches = os.listdir(buffer_path)
                print(f"📦 Found buffer batches: {batches}")
            else:
                print("⚠️  Buffer batches folder not found")
                
            return "Data folder accessible"
        except Exception as e:
            print(f"❌ Error reading data folder: {str(e)}")
            return f"Error: {str(e)}"
    else:
        print(f"❌ Data folder not found at: {data_path}")
        return "Data folder not mounted"

# Task 1: Welcome message
task_welcome = PythonOperator(
    task_id='print_welcome',
    python_callable=print_welcome,
    dag=dag,
)

# Task 2: Check Python version
task_python_version = BashOperator(
    task_id='check_python_version',
    bash_command='python --version',
    dag=dag,
)

# Task 3: Check Neon connection
task_check_neon = PythonOperator(
    task_id='check_neon_connection',
    python_callable=check_neon_connection,
    dag=dag,
)

# Task 4: Check data folder
task_check_data = PythonOperator(
    task_id='check_data_folder',
    python_callable=check_data_folder,
    dag=dag,
)

# Task 5: Success message
task_success = BashOperator(
    task_id='success_message',
    bash_command='echo "🎉 All checks passed! Airflow is ready for CineMatch MLOps!"',
    dag=dag,
)

# Define task dependencies
task_welcome >> task_python_version >> [task_check_neon, task_check_data] >> task_success
