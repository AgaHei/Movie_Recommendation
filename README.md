# MovieLens 25M - ML Recommendation System

A comprehensive machine learning project for building a movie recommendation system using the MovieLens 25M dataset. It is built as part of the AI Architect certification within the Data Science and Engineering Lead Bootcamp at JEDHA (Final Project).

**Note**: This is a **team project in active development**. The README and codebase will be continuously updated as the project progresses.

## 👥 Team & Contributions

This project is a collaborative effort across different domains:

| Team Member | Role | Focus Area |
|-------------|------|-----------|
| **Agnès** | Data Lead | Data exploration, preparation, feature engineering, and dimensionality reduction |
| **Julien** | ML Engineer | Model development, training, hyperparameter tuning, and performance optimization |
| **Matéo** | MLOps Engineer | Deployment pipelines, monitoring, and production infrastructure |

**Status**: 🚧 In Progress - Core data pipeline complete, ML model development underway, MLOps integration coming soon.

## 📋 Project Overview

This project implements a recommendation system using collaborative filtering and hybrid approaches. It includes:

- **Exploratory Data Analysis (EDA)** of the MovieLens 25M dataset
- **Data Preparation** with feature engineering and dimensionality reduction
- **Model Training** (baseline collaborative filtering + hybrid models)
- **Temporal data splitting** to simulate real-world deployment scenarios

## 📁 Project Structure

```
Movie_Recommendation/
├── notebooks/
│   ├── 01_EDA_MovieLens_25M.ipynb          # Exploratory data analysis
│   └── 02_Data_Preparation_MovieLens_25M.ipynb  # Data preparation & feature engineering
├── ingestion_scripts/
│   ├── initial_load_lighter_dataset.py      # Transfer prepared data to Neon database
│   ├── check_rows.py                        # Utility to verify row counts in Neon
│   ├── .env                                 # Database credentials (not tracked)
│   └── .env.example                         # Template for database credentials
├── airflow/                                  # Apache Airflow orchestration
│   ├── dags/                                # Airflow DAG definitions (coming soon)
│   ├── logs/                                # Airflow logs (not tracked)
│   ├── plugins/                             # Custom Airflow plugins (not tracked)
│   ├── docker-compose.yml                   # Airflow services configuration
│   ├── Dockerfile                           # Custom Airflow image with dependencies
│   ├── requirements.txt                     # Airflow-specific Python packages
│   └── .env                                 # Airflow environment variables (not tracked)
├── raw/                                      # Raw MovieLens 25M data files (not tracked)
├── prepared/                                 # Processed data artifacts (not tracked)
│   ├── ratings_initial_ml.parquet          # 1M row reduced dataset for Neon
│   └── buffer_batches/                      # 5 weekly batches for Airflow ingestion
├── .venv/                                    # Virtual environment (not tracked)
├── requirements.txt                          # Python dependencies
├── README.md                                 # This file
└── .gitignore                                # Git ignore rules
```

## 🎯 Dataset

The **MovieLens 25M** dataset contains:

- **25 million ratings** from 162,541 users on 59,047 movies
- **User ratings** on a 0.5-5 star scale
- **Movie metadata**: titles, genres
- **Genome tags**: 1,128 tag relevance scores per movie
- **Temporal data**: ratings from 1995 to 2019

**Source**: [GroupLens Research - MovieLens 25M](https://grouplens.org/datasets/movielens/25m/)

**Note**: The `raw/` folder is excluded from Git (see `.gitignore`). Each team member must download the data independently.

## 🚀 Quick Start

### For Data Analysis
```bash
# Clone the repository
git clone https://github.com/AgaHei/Movie_Recommendation.git
cd Movie_Recommendation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download MovieLens 25M dataset
# Visit: https://grouplens.org/datasets/movielens/25m/
# Extract to raw/ folder

# Run notebooks in order
# 1. notebooks/01_EDA_MovieLens_25M.ipynb
# 2. notebooks/02_Data_Preparation_MovieLens_25M.ipynb
```

### For Airflow/MLOps
```bash
# Ensure Docker Desktop is running

# Navigate to airflow directory
cd airflow

# Create .env file with your credentials
cp .env.example .env
# Edit .env with your NEON_CONNECTION_STRING

# Start Airflow
docker-compose up -d

# Access Web UI at http://localhost:8080
# Username: airflow | Password: airflow

# Stop Airflow when done
docker-compose down
```


## 📥 Data Management

## � Database: Neon PostgreSQL

We use **Neon** (serverless PostgreSQL) for storing prepared data and enabling the MLOps pipeline.

### Free Tier Constraint
- **Storage limit**: 512 MB
- **Challenge**: Full dataset (~22,5M rows in `ratings_train.parquet` and `ratings_test.parquet` altogether) exceeds this limit
- **Solution**: Created a reduced initial dataset with **1M most recent rows extracted from `ratings_test.parquet`** (=> new file created `ratings_initial_ml.parquet`)

### What's in Neon?
- `ratings` table: 1M rows (700K train + 300K test)
- `movies` table: 62K movies with features
- `ratings_buffer` table: Empty structure (batches ingested by Airflow)
- Metadata tables: `ingestion_metadata`, `model_metrics`, `drift_alerts`

## 🔄 Apache Airflow Orchestration

We use **Apache Airflow** to orchestrate data pipelines, model training, and monitoring workflows.

### Setup & Architecture

**Containerized Setup**:
- **Custom Docker Image**: Extends `apache/airflow:2.8.1-python3.11` with project dependencies
- **Services**:
  - `airflow-webserver`: Web UI (http://localhost:8080)
  - `airflow-scheduler`: Task scheduling and execution
  - `postgres`: Metadata database for Airflow
- **Persistent Volumes**: DAGs, logs, and plugins are mounted from local directories

### Airflow Configuration

**Environment Variables** (`.env` in `airflow/` folder):
```env
NEON_CONNECTION_STRING=postgresql://[user]:[password]@[host]/[database]
MLFLOW_TRACKING_URI=http://mlflow:5000  # (Coming soon)
```

**Installed Packages** (via custom Dockerfile):
- pandas, pyarrow - Data processing
- scipy - Statistical analysis
- requests - HTTP API calls
- python-dotenv - Environment management

### Getting Started with Airflow

1. **Prerequisites**:
   ```bash
   # Install Docker Desktop (Windows/Mac) or Docker Engine (Linux)
   # Ensure Docker Compose is installed
   ```

2. **Start Airflow**:
   ```bash
   cd airflow
   docker-compose up -d
   ```

3. **Access Web UI**:
   - URL: http://localhost:8080
   - Username: `airflow`
   - Password: `airflow`

4. **Stop Airflow**:
   ```bash
   docker-compose down
   ```

### Planned DAGs (Coming Soon)

1. **Batch Ingestion DAG**: Weekly data ingestion from `prepared/buffer_batches/`
2. **Model Training DAG**: Periodic retraining on new data
3. **Drift Detection DAG**: Monitor data quality and distribution shifts
4. **Model Deployment DAG**: Deploy trained models to production

### Why Airflow?

- **Reproducibility**: Version-controlled workflows
- **Scheduling**: Automated batch processing (weekly data ingestion)
- **Monitoring**: Track pipeline health and failures
- **Scalability**: Distributed task execution
- **Integration**: Connect data pipelines with MLflow and deployment systems

## �📊 Key Features

### Data Preparation
- **Memory-efficient processing**: Handles 25M+ rows without OOM errors
- **Feature engineering**: 
  - Genre one-hot encoding
  - PCA dimensionality reduction (1,128 → 64 genome tag embeddings)
  - Temporal features extraction
- **Temporal splitting**: 70% train / 20% test / 10% buffer (chronological)

### Artifacts Generated
After running the preparation notebook, the following files are created in `prepared/`:

**Full dataset (for local development)**:
- `ratings_train.parquet` (~1.5 GB) - Training interactions (17.5M rows)
- `ratings_test.parquet` (~430 MB) - Test interactions (5M rows)
- `ratings_buffer.parquet` (~215 MB) - Continuous monitoring buffer (2.5M rows)
- `movie_features_small.parquet` (~500 MB) - Compact movie features with PCA embeddings
- `movie_features_uni.parquet` - Full movie features (reference only)
- `movie_embeddings.parquet` - PCA genome embeddings (reference only)

**Reduced dataset (for Neon free tier)**:
- `ratings_initial_ml.parquet` - 1M most recent rows from test set
- `buffer_batches/batch_w{1-5}.parquet` - 5 weekly batches for Airflow ingestion

## 🔬 Analysis Highlights

### From EDA Notebook:
- **Matrix sparsity**: 99.74% (extreme sparsity requires advanced techniques)
- **User behavior**: Power users (200+ ratings) contribute 77% of all ratings
- **Rating bias**: Mean user rating is 3.68 (positive bias)
- **Temporal trends**: Clear rating activity patterns over time
- **Genre insights**: Drama, Comedy, and Thriller are most common

### From Preparation Notebook:
- **PCA explained variance**: ~90% with 64 components
- **Memory optimization**: Reduced from ~110 GB to ~2.6 GB total
- **Temporal integrity**: No data leakage in train/test/buffer splits

## 🛠️ Technologies Used

### Data Processing & ML
- **Python 3.12**
- **pandas** - Data manipulation
- **NumPy** - Numerical computing
- **scikit-learn** - Machine learning & PCA
- **matplotlib & seaborn** - Visualization
- **PyArrow** - Efficient Parquet I/O
- **scipy** - Statistical analysis for drift detection

### Orchestration & Infrastructure
- **Apache Airflow 2.8.1** - Workflow orchestration
- **Docker & Docker Compose** - Containerization
- **PostgreSQL 13** - Airflow metadata database
- **Neon (Serverless PostgreSQL)** - Data warehouse

### MLOps & Deployment (Coming Soon)
- **MLflow** - Model tracking and versioning
- **FastAPI** - REST API for serving recommendations

## 📝 Next Steps
1. **Baseline Model**: Train SVD/ALS collaborative filtering
2. **Hybrid Model**: Integrate movie embeddings with collaborative signals
3. **Evaluation**: Compare models on test set using RMSE, MAE, Precision@K
4. **Monitoring**: Detect drift using buffer data
5. **Deployment**: Build API for real-time recommendations

## 🚀 Project Roadmap & Team Coordination

### Phase 1: Data Pipeline (✅ Complete - Agnès)
- [x] EDA and dataset exploration
- [x] Data preparation and feature engineering
- [x] Dimensionality reduction (PCA)
- [x] Temporal splitting (train/test/buffer)
- [x] Neon database integration (reduced 1M row dataset)
- [x] Buffer batch preparation for Airflow
- [x] Data transfer scripts and verification utilities
- [x] Data documentation and quality metrics
- [x] Apache Airflow setup with Docker
- [x] Custom Airflow image with project dependencies
- [ ] Airflow DAGs for batch ingestion and monitoring

### Phase 2: Model Development (🚧 In Progress - Julien)
- [ ] Baseline collaborative filtering models (SVD, ALS, NMF)
- [ ] Hybrid model architecture design
- [ ] Hyperparameter tuning and optimization
- [ ] Performance benchmarking and evaluation
- [ ] Model selection and finalization

### Phase 3: MLOps & Deployment (⏳ Coming Soon - Matéo)
- [ ] Model versioning and registry
- [ ] CI/CD pipeline setup
- [ ] Containerization and deployment infrastructure
- [ ] Monitoring and alerting systems
- [ ] A/B testing framework
- [ ] Documentation and runbooks

### How to Contribute

**For team members**:
1. Check the relevant phase above for your role
2. Update progress by modifying this README
3. Document changes and new features
4. Keep notebooks well-commented for handoffs between phases

## 📄 License

This project uses the MovieLens 25M dataset provided by GroupLens Research. Please cite:

```
F. Maxwell Harper and Joseph A. Konstan. 2015. 
The MovieLens Datasets: History and Context. 
ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19. 
https://doi.org/10.1145/2827872
```

## 👥 Project Team

This project is developed collaboratively by:

- **Agnès** - Data Lead & Data Engineering
- **Julien** - ML Engineering
- **Matéo** - MLOps & Infrastructure

## 🙏 Acknowledgments

- [GroupLens Research](https://grouplens.org/) for the MovieLens dataset
- [Jedha Bootcamp](https://www.jedha.co/) for project guidance and mentorship

---

**Last Updated**: December 2025  
**Status**: 🚧 Active Development
