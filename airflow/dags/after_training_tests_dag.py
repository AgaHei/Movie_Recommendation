from __future__ import annotations

from datetime import datetime
import os

from airflow import DAG
from airflow.operators.bash import BashOperator

CINEMATCH_ROOT = os.environ.get("CINEMATCH_ROOT", "/opt/airflow/cinematch")
PROJECT_DIR = os.environ.get(
    "MLFLOW_TRAINING_DIR",
    os.path.join(CINEMATCH_ROOT, "movie-recommendation-mlflow", "mlflow_training"),
)

with DAG(
    dag_id="after_training_tests_dag",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["ci", "tests", "after-training"],
) as dag:
    tests_after = BashOperator(
        task_id="tests_after_training",
        bash_command=f"""
        set -e
        cd {PROJECT_DIR}
        VENV_DIR=".venv_ci_after"
        if [ ! -d "$VENV_DIR" ]; then
          python -m venv "$VENV_DIR"
          "$VENV_DIR/bin/pip" install -r requirements.txt
        fi
        export PYTHONPATH="$PWD"
        "$VENV_DIR/bin/pytest" -q tests/after_training
        """,
    )
