"""
Tests related to Airflow DAG structure.
"""

from airflow.models import DagBag

def test_dag_is_loaded():
    dagbag = DagBag(include_examples=False)
    dag = dagbag.get_dag("buffer_ingestion_weekly")
    assert dag is not None

def test_dag_tasks_exist():
    dagbag = DagBag(include_examples=False)
    dag = dagbag.get_dag("buffer_ingestion_weekly")

    task_ids = [task.task_id for task in dag.tasks]

    assert "ingest_batch_7" in task_ids
    assert "check_buffer_status" in task_ids

def test_dag_dependencies():
    dagbag = DagBag(include_examples=False)
    dag = dagbag.get_dag("buffer_ingestion_weekly")

    ingest = dag.get_task("ingest_batch_7")
    status = dag.get_task("check_buffer_status")

    assert status.task_id in ingest.downstream_task_ids
