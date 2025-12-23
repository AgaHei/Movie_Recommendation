"""
CI-style DAG to run pytest inside the Airflow container before pipelines.
Requires the repo to be mounted at /opt/airflow/data (set in docker-compose).
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

with DAG(
    dag_id="ci_run_tests",
    start_date=datetime(2025, 1, 1),
    schedule=None,  # manual trigger; chain it before other DAGs if desired
    catchup=False,
    tags=["ci", "tests"],
) as dag:
    run_pytest = BashOperator(
        task_id="run_pytest",
        bash_command=(
            "cd /opt/airflow/data/airflow && "
            "python -m pytest /opt/airflow/data/airflow/tests"
        ),
    )

    # Trigger downstream DAG only if tests pass
    trigger_downstream = TriggerDagRunOperator(
        task_id="trigger_buffer_ingestion",
        trigger_dag_id="buffer_ingestion_weekly",
        reset_dag_run=True,
        wait_for_completion=False,
    )

    run_pytest >> trigger_downstream
