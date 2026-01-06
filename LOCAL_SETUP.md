# Cinematch Local Setup (3 repos, 3 devs)

This guide documents the local setup for the whole project when the three
repositories are used side by side by three developers.

## Folder layout (shared by everyone)

Clone the repos next to each other:

```
cinematch/
├── Movie_Recommendation/
├── movie-recommendation-mlflow/
└── movie-recommendation-api/
```

## Common prerequisites

- Docker Desktop running
- Python 3.11+
- Git

## Developer 1: Orchestration (Airflow + pipelines)

### Airflow env file

Create `Movie_Recommendation/airflow/.env`:

```
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=50000

NEON_CONNECTION_STRING=postgresql://...
MLFLOW_TRACKING_URI=https://...

# Path mapping used by DAGs in the Airflow container
CINEMATCH_ROOT=/opt/airflow/cinematch
# Optional override for tests DAG
MLFLOW_TRAINING_DIR=/opt/airflow/cinematch/movie-recommendation-mlflow/mlflow_training
```

### Start Airflow

```
cd Movie_Recommendation/airflow
docker compose up -d
```

Airflow UI:
- http://localhost:8080
- Login: `airflow` / `airflow`

## Developer 2: Training (MLflow)

### MLflow training env file

Create `movie-recommendation-mlflow/mlflow_training/.env`:

```
NEON_CONNECTION_STRING=postgresql://...
MLFLOW_TRACKING_URI=https://...

# Required for remote artifact store (S3)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=...
MLFLOW_ARTIFACT_ROOT=s3://...
MLFLOW_BACKEND_STORE_URI=postgresql://...
```

### Dataset files

The training script expects `raw/genome-scores.csv` (and related MovieLens files)
relative to the `mlflow_training/` folder. Use one of these options:

Option A (recommended): download once and symlink
```
python Movie_Recommendation/scripts/download_dataset.py
mkdir -p movie-recommendation-mlflow/mlflow_training
ln -s ../../Movie_Recommendation/raw movie-recommendation-mlflow/mlflow_training/raw
```

Option B: copy the raw folder
```
python Movie_Recommendation/scripts/download_dataset.py
cp -R Movie_Recommendation/raw movie-recommendation-mlflow/mlflow_training/raw
```

### Run training locally

```
cd movie-recommendation-mlflow/mlflow_training
python train_mlflow.py --data-path /tmp/training_data/ratings_combined.parquet --test-path /tmp/training_data/ratings_test.parquet
```

## Developer 3: API (FastAPI)

### API env file

Create `movie-recommendation-api/fastapi/.env`:

```
DB_URL=postgresql://...
MLFLOW_TRACKING_URI=https://...
MODEL_NAME=movie_recommendation_hybrid_system
MODEL_VERSION=1
```

### Run API locally

```
cd movie-recommendation-api/fastapi
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Shared notes

- Airflow DAGs use `CINEMATCH_ROOT` to locate the other repos in the container.
- The retraining DAG requires `mlflow` in the Airflow image; it is installed
  from `Movie_Recommendation/airflow/requirements.txt`.
- If you change DAG code, the scheduler reloads it within ~1 minute.
