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
IMAGE_NAME = os.environ.get("MLFLOW_TRAINING_IMAGE", "mlflow-training")
TAG = "{{ ds_nodash }}-{{ run_id | replace(':','_') | replace('+','_') }}"

with DAG(
    dag_id="ci_docker_build_test",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["ci", "docker", "tests"],
) as dag:
    tests_before = BashOperator(
        task_id="tests_before_training",
        bash_command=f"""
        set -e
        cd {PROJECT_DIR}
        VENV_DIR=".venv_ci"
        if [ ! -d "$VENV_DIR" ]; then
          python -m venv "$VENV_DIR"
          "$VENV_DIR/bin/pip" install -r requirements.txt
        fi
        export PYTHONPATH="$PWD"
        "$VENV_DIR/bin/pytest" -q tests/before_training
        """,
    )

    docker_build = BashOperator(
        task_id="docker_build",
        bash_command=f"""
        set -e
        cd {PROJECT_DIR}
        docker build -t {IMAGE_NAME}:{TAG} .
        """,
    )

    docker_smoke_tests = BashOperator(
        task_id="docker_smoke_tests",
        bash_command=f"""
        set -e
        cd {PROJECT_DIR}
        docker run --rm \
          {IMAGE_NAME}:{TAG} \
          bash -lc "export PYTHONPATH=/app && pytest -q tests/before_training"
        """,
    )

    tests_before >> docker_build >> docker_smoke_tests
