from __future__ import annotations

from datetime import datetime
import os

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = os.environ.get("MLFLOW_TRAINING_DIR", "/opt/airflow/mlflow_training")
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
        pytest -q tests/before_training
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
          -v "$PWD":/app \
          -w /app \
          {IMAGE_NAME}:{TAG} \
          bash -lc "pytest -q tests/before_training"
        """,
    )

    tests_before >> docker_build >> docker_smoke_tests
