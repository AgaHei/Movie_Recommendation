# 🎬 CineMatch - MLOps Movie Recommendation System

> A production-grade movie recommendation system demonstrating modern MLOps practices with automated drift detection, continuous training, and seamless deployment.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Airflow](https://img.shields.io/badge/Airflow-2.8-017CEE.svg)](https://airflow.apache.org/)
[![MLflow](https://img.shields.io/badge/MLflow-2.9-0194E2.svg)](https://mlflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Deployed Applications](#-deployed-applications)
- [Jury Presentation Components](#-jury-presentation-components-january-8th-2026)
- [Results](#-results)
- [Team](#-team)
- [Repository Structure](#-repository-structure)
- [Comprehensive Airflow DAGs](#-comprehensive-airflow-dags)
- [Documentation](#-documentation)
- [Future Enhancements](#-future-enhancements)
- [Learning Outcomes](#-learning-outcomes)
- [Acknowledgments](#-acknowledgments)
- [License](#-license)
- [Project Timeline](#-project-timeline)

---

## 🎯 Overview

CineMatch is a **complete MLOps pipeline** for movie recommendations, built as the capstone project for the Jedha Data Science & Engineering Lead Bootcamp (December 2025 - January 2026). 

The system demonstrates **industry-standard machine learning operations**, including:
- 🔄 Automated data ingestion and monitoring
- 📊 Statistical drift detection with multiple tests
- 🤖 Continuous model training and deployment
- 🚀 Production-ready REST API
- 📈 Complete observability and audit trails

**What makes this project special:**
- Real-world MLOps architecture (not just a Jupyter notebook!)
- Continuous monitoring simulating 7 weeks of production operation
- Model retraining triggered by data drift
- Complete CI/CD/CT/CM pipeline
- Free-tier infrastructure (€0 budget)

**Please note that this project is a comprehensive team work nearing completion with multiple deployed components and comprehensive monitoring systems.**
---

## ✨ Key Features

### 🔍 Intelligent Drift Detection
- **Statistical Tests:** Kolmogorov-Smirnov, mean change, variance analysis
- **Threshold-Based Decisions:** Configurable sensitivity for production needs
- **Progressive Monitoring:** Accumulates evidence over time before triggering retraining
- **Complete Audit Trail:** Every decision logged to database

### 🔄 Automated Continuous Training
- **Manual Trigger via Airflow:** Retraining triggered manually when drift detected
- **MLflow Experiment Tracking:** All training runs versioned and comparable
- **Model Registry:** Automatic promotion of improved models to production
- **Performance Monitoring:** RMSE, MAE, Precision@K tracked over time

### 🚀 Production Deployment
- **FastAPI REST API:** Modern, fast, auto-documented endpoints
- **Docker Containerization:** Reproducible deployment anywhere
- **HF Hosting:** Deployed on Hugging Face Spaces (free tier)
- **Model Versioning:** Seamless updates without downtime

### 📊 Complete Observability
- **Airflow UI:** Visual pipeline monitoring
- **Neon Database:** Centralized data and metadata storage
- **MLflow Dashboard:** Experiment comparison and model selection
- **Detailed Logging:** Every operation tracked and queryable

---

## 🏗️ Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    CINEMATCH MLOPS PIPELINE                 │
└─────────────────────────────────────────────────────────────┘

Data Layer            Orchestration & Training     Tracking & Deployment
    │                          │                              │
    ▼                          ▼                              ▼
┌─────────┐             ┌──────────────┐            ┌─────────────────┐
│  Neon   │◀──────────▶│   Airflow    │──────────▶│     MLflow      │
│  (DB)   │             │   (Docker)   │            │  (Experiments)  │
│         │             │              │            │                 │
│ • Data  │             │ • Ingestion  │            │ • Training      │
│ • Meta  │             │ • Monitoring │            │ • Evaluation    │
│ • Logs  │             │ • Manual     │            │ • Model Registry│
│         │             │   Retraining │            │                 │
└─────────┘             └──────────────┘            └────────┬───────-┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │    FastAPI       │
                                                    │  (Production)    │
                                                    └──────────────────┘
```

**[📖 Detailed Architecture Documentation](docs/mlops/architecture-diagram.md)**

---

## 🛠️ Tech Stack

### Data & Storage
- **Database:** Neon PostgreSQL (Serverless, 512 MB)
- **Data Format:** Apache Parquet
- **Processing:** Pandas 2.1+

### Orchestration & Monitoring
- **Workflow Engine:** Apache Airflow 2.8
- **Containerization:** Docker + Docker Compose
- **Drift Detection:** SciPy (statistical tests)

### Machine Learning
- **ML Framework:** scikit-surprise (collaborative filtering)
- **Experiment Tracking:** MLflow 2.9 (hosted on Dagshub)
- **Dataset:** MovieLens 25M (reduced to 1M for constraints)

### Deployment
- **API Framework:** FastAPI 0.109
- **Server:** Uvicorn (ASGI)
- **Hosting:** Hugging Face
- **Manual Operations:** Airflow-based retraining

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (for Airflow)
- **Python 3.11+** (for local development)
- **Git** (for version control)
- **Neon Account** (free tier: [neon.tech](https://neon.tech))

### Installation

```bash
# 1. Clone the main repository
git clone https://github.com/AgaHei/Movie_Recommendation.git
cd cinematch

# 2. Set up Airflow environment
cd airflow/
cp .env.example .env
# Edit .env with your Neon credentials

# 3. Start Airflow
docker-compose up -d

# 4. Access Airflow UI
open http://localhost:8080
# Login: airflow / airflow

# Additional Components:
# - MLflow Experiments: https://github.com/JulienRouillard/movie-recommendation-mlflow
# - FastAPI Service: https://github.com/JulienRouillard/movie-recommendation-api
```

### Running Your First Pipeline

```bash
# 1. Trigger buffer ingestion (Week 1)
# In Airflow UI: Find "buffer_ingestion_weekly" → Click Play ▶️

# 2. Run drift monitoring
# In Airflow UI: Find "drift_monitoring" → Click Play ▶️

# 3. Check results in Neon
# Query: SELECT * FROM drift_alerts ORDER BY alert_date DESC;
```

**[📖 Detailed Setup Guide](docs/airflow/01-airflow-setup.md)**

### 🌐 Deployed Applications

#### Production Services (Live)
- **🤖 MLflow Experiments & Model Registry**  
  https://julienrouillard-mlflow-movie-recommandation.hf.space/  
  *Complete experiment tracking, model comparison, and versioning*

- **🚀 FastAPI Recommendation Service**  
  https://julienrouillard-movie-recommendation-api.hf.space/docs  
  *Production REST API with interactive documentation*

#### Deployed Development Tools
- **📊 MLOps Monitoring Dashboard** (Streamlit)  
  https://movierecommendation-hjhgd45vqk4zdaprsh6arw.streamlit.app/  
  *Real-time drift monitoring, pipeline status, and system health*

- **🎬 Movie Recommendation Demo** (Streamlit)  
  https://julienrouillard-movie-recommendation-interface.hf.space/  
  *Interactive recommendation system demonstration*

---

## 🎯 Jury Presentation Components (January 8th, 2026)

### 🖥️ **Live Demo Applications**

#### 1. **📊 MLOps Monitoring Dashboard** (Streamlit)
**Live Demo:** https://movierecommendation-hjhgd45vqk4zdaprsh6arw.streamlit.app/

**Key Features for Presentation:**
- ✨ **Real-time drift detection visualization** - KS statistics over time
- 📈 **System health metrics** - Buffer size, alert counts, pipeline status  
- 🔍 **Interactive filtering** - Filter alerts by date range and severity
- 📋 **Complete audit trail** - All MLOps decisions logged and queryable
- 🎨 **Professional UI** - Production-ready monitoring interface

**Demo Flow:**
1. Overview page → System metrics and current status
2. Drift Monitoring → Show Week 7 drift detection trigger  
3. Pipeline Status → MLOps architecture and retraining decisions

#### 2. **🎬 Movie Recommendation Demo** (Streamlit)
**Live Demo:** https://julienrouillard-movie-recommendation-interface.hf.space/  
**Interactive User Experience Demo**

**Key Features for Presentation:**
- 🔍 **Movie search and selection** - Browse MovieLens catalog
- ⭐ **Personal rating interface** - Rate movies to build user profile
- 🤖 **Real-time recommendations** - Generate personalized suggestions
- 📊 **Recommendation explanations** - Show why movies were recommended  
- 🎯 **Model performance metrics** - Display accuracy and confidence scores

**Demo Flow:**
1. User ID selection → Rate sample movies
2. Recommendation generation → Show personalized results (top 50 recommended movies)
3. Model insights → Explain collaborative filtering approach

### 🌐 **Production Deployments** (Live URLs)
- **MLflow Experiments:** https://julienrouillard-mlflow-movie-recommandation.hf.space/
- **FastAPI Service:** https://julienrouillard-movie-recommendation-api.hf.space/docs

### 💡 **Presentation Strategy**
> **"Complete MLOps ecosystem demonstration: From data ingestion through drift detection to model retraining, with both technical monitoring dashboards and user-facing recommendation interfaces."**

---


## 📊 Results

### 7-Week Drift Monitoring Simulation

Our simulation demonstrated progressive drift detection over 3 weeks:

    | Weeks | Buffer Size | KS Statistic | Mean Change | Decision                 |
    |------|-------------|------------ --|-------------|--------------------------|
    | **1-6**  | 600k ratings | 0.014    | 0.011       | ✅ No drift - Continue   |
    | **7**    | 100K ratings | 0.097    | 0.065        | 🚨 DRIFT Retrain needed |



**Key Achievement:** Automated system detected drift and triggered retraining, resulting in measurable model improvement!

**[📈 Detailed Results & Analysis](docs/mlops/weekly-simulation-log.md)**

---

## 👥 Team

**Jedha Data Science & Engineering Bootcamp - Final Project (December 2025)**

### Team Members

| Name | Role | Responsibilities |
|------|------|------------------|
| **[Agnès]** | Data Pipeline & Monitoring | Airflow orchestration, drift detection, data engineering, Neon database design |
| **[Julien]** | Model Training & Experimentation | Collaborative filtering models, MLflow integration, hyperparameter tuning, FastAPI development |
| **[Matéo]** | Deployment & Project coordination| Testing at all stages, Docker containerization, deployment |

### Collaboration

- **Version Control:** Git + GitHub
- **Communication:** Discord
- **Documentation:** Markdown in `/docs`

---

## 🏗️ Repository Structure

The CineMatch project is organized across **3 specialized GitHub repositories**:

### 📂 Main Repository - Data Pipeline & Orchestration
**[🔗 AgaHei/Movie_Recommendation](https://github.com/AgaHei/Movie_Recommendation)**
```
cinematches/
├── airflow/                 # Orchestration & DAGs
│   ├── dags/
│   │   ├── buffer_ingestion_weekly.py     # Data ingestion pipeline
│   │   ├── drift_monitoring.py            # Statistical drift detection
│   │   ├── trigger_retraining_dag.py      # Model retraining trigger
│   │   └── data_testing.py                # Data quality validation
│   ├── docker-compose.yml
│   └── .env                 # Database connections
├── dashboard/              # MLOps Monitoring Dashboard
│   ├── cinematch_dashboard.py             # Streamlit monitoring app
│   └── README_DASHBOARD.md  # Dashboard setup guide
├── docs/                   # Comprehensive documentation
└── data/                   # Processed datasets
```

### 🤖 MLflow Repository - Model Training & Experiments
**[🔗 JulienRouillard/movie-recommendation-mlflow](https://github.com/JulienRouillard/movie-recommendation-mlflow)**
- Collaborative filtering model implementations
- MLflow experiment tracking and model registry
- Hyperparameter optimization
- Model evaluation and comparison
- **Live Demo:** https://julienrouillard-mlflow-movie-recommandation.hf.space/

### 🚀 FastAPI Repository - Production API
**[🔗 JulienRouillard/movie-recommendation-api](https://github.com/JulienRouillard/movie-recommendation-api)**
- REST API endpoints for movie recommendations
- Model serving and inference pipeline
- Docker containerization
- API documentation and testing
- **Live API:** https://julienrouillard-movie-recommendation-api.hf.space/docs

---

## 📊 Comprehensive Airflow DAGs

Our MLOps pipeline includes **7 specialized DAGs** handling all aspects of the ML lifecycle:

### 📊 Data Pipeline DAGs

#### 🔄 Data Ingestion - `buffer_ingestion_weekly.py`
- **Purpose:** Simulates weekly data ingestion from production systems
- **Features:** Incremental loading, data validation, schema enforcement
- **Trigger:** Weekly schedule or manual execution
- **Output:** New ratings data loaded to buffer tables

### 🔍 Monitoring & Analysis DAGs

#### 📈 Drift Monitoring - `drift_monitoring.py`
- **Purpose:** Statistical drift detection using KS tests and distribution analysis
- **Features:** 
  - Kolmogorov-Smirnov statistical testing
  - Mean and variance change detection  
  - Configurable thresholds and sensitivity
  - Cumulative evidence accumulation
- **Trigger:** Daily monitoring schedule
- **Output:** Drift alerts and retraining recommendations

#### 🎯 Batch Predictions - `batch_predictions_dag.py`
- **Purpose:** Model drift detection through performance evaluation
- **Features:**
  - Batch prediction processing via REST API
  - MAE/RMSE performance monitoring  
  - Automated retraining trigger on performance degradation
  - Prediction results storage and tracking
- **Trigger:** Triggered by buffer ingestion with batch_id
- **Output:** Performance metrics and drift alerts

### 🤖 Model Training & Deployment DAGs

#### 🔄 Retraining Pipeline - `trigger_retraining_dag.py`
- **Purpose:** Orchestrates model retraining when drift is detected
- **Features:**
  - Automated model training with accumulated buffer data
  - MLflow integration for experiment tracking
  - Model validation and performance comparison
  - Automated promotion of improved models
- **Trigger:** Manual execution when drift alerts are confirmed
- **Output:** New model versions in MLflow registry

#### ✅ After Training Tests - `after_training_tests_dag.py`
- **Purpose:** Post-training validation and quality assurance
- **Features:**
  - Automated testing of newly trained models
  - Model performance validation
  - Integration testing with MLflow
- **Trigger:** Manual execution after model retraining
- **Output:** Training validation reports

### 🚀 CI/CD & Testing DAGs

#### 🧪 CI Test Runner - `ci_run_tests.py`
- **Purpose:** Continuous integration testing before pipeline execution
- **Features:**
  - Pytest execution within Airflow container
  - Automated downstream DAG triggering on success
  - Pre-deployment validation
- **Trigger:** Manual execution for CI workflows
- **Output:** Test results and pipeline validation

#### 🐳 Docker Build Testing - `ci_docker_build_test.py`
- **Purpose:** Docker containerization testing and validation
- **Features:**
  - Docker image building and testing
  - Container environment validation
  - Pre-training Docker setup verification
- **Trigger:** Manual execution for deployment validation
- **Output:** Docker build status and container readiness

---

## 📚 Documentation

Comprehensive documentation is available in the [`/docs`](docs/) directory:

### Getting Started
- [📖 Architecture Overview](docs/mlops/architecture-diagram.md) - Complete system design
- [🚀 Airflow Setup Guide](docs/airflow/01-airflow-setup.md) - Step-by-step installation

### Data Pipeline
- [📊 Data Pipeline Overview](docs/data/data-pipeline-overview.md) - Dataset processing
- [🗄️ Database Schema](docs/data/neon-schema.md) - Neon table reference

### MLOps Workflows
- [📦 Buffer Ingestion Guide](docs/airflow/02-buffer-ingestion.md) - Data loading
- [🔍 Drift Monitoring Guide](docs/airflow/03-drift-monitoring.md) - Drift detection
- [📈 Simulation Results](docs/mlops/weekly-simulation-log.md) - 3-week analysis


---

## 🚀 Future Enhancements

### Planned Improvements (Phase 2)

#### 🤖 Automated CI/CD with GitHub Actions
- **Automated Retraining:** Trigger training via GitHub API when drift detected
- **Continuous Deployment:** Auto-deploy improved models to production
- **Pipeline Integration:** Seamless Airflow → GitHub Actions workflow
- **Benefits:** Zero-touch MLOps, faster iteration cycles

#### 📏 Advanced Monitoring
- **Real-time Dashboards:** Grafana/Plotly integration
- **Alert System:** Email/Slack notifications for drift events
- **Performance Tracking:** A/B testing for model versions
- **Data Quality Monitoring:** Schema validation, anomaly detection

#### 🌐 Production Scalability
- **Kubernetes Deployment:** Container orchestration at scale
- **Load Balancing:** Handle high-traffic recommendation requests
- **Caching Layer:** Redis for faster recommendation serving
- **Multi-model Serving:** Support for different recommendation algorithms

#### 📋 Enhanced ML Features
- **Deep Learning Models:** Neural collaborative filtering
- **Content-based Filtering:** Hybrid recommendation approach
- **Online Learning:** Real-time model updates
- **Explainable AI:** Recommendation reasoning

---

## 🎓 Learning Outcomes

This project demonstrates skills in:

### MLOps Practices
✅ **Continuous Integration (CI)** - Multi-repo development with quality controls  
✅ **Continuous Deployment (CD)** - Automated deployments to Hugging Face Spaces  
✅ **Continuous Training (CT)** - Drift-triggered retraining with MLflow tracking  
✅ **Continuous Monitoring (CM)** - Comprehensive drift detection and dashboard monitoring  

### Technical Skills
✅ **Data Engineering** - ETL pipelines, database design, data quality  
✅ **Machine Learning** - Collaborative filtering, model evaluation  
✅ **DevOps** - Docker, CI/CD, orchestration, cloud deployment  
✅ **Software Engineering** - API design, testing, documentation  

### Tools & Technologies
✅ **Airflow** - Workflow orchestration at scale  
✅ **MLflow** - Experiment tracking and model registry  
✅ **FastAPI** - Modern API development  
✅ **Docker** - Containerization and deployment  
✅ **PostgreSQL** - Relational database design  
🔄 **GitHub Actions** - CI/CD automation (future enhancement)  

---

## 🙏 Acknowledgments

### Dataset
**MovieLens 25M Dataset**  
F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19.  
https://grouplens.org/datasets/movielens/

### Technologies
- **Apache Airflow** - [airflow.apache.org](https://airflow.apache.org/)
- **MLflow** - [mlflow.org](https://mlflow.org/)
- **FastAPI** - [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **Neon** - [neon.tech](https://neon.tech/)

### Bootcamp
**Jedha Bootcamp** - Data Science & Engineering Lead Bootcamp
Special thanks to our instructors for guidance throughout the project!

---

## 📝 License

This project is an academic work created for the Jedha Bootcamp final project (December 2025 - January 2026).  
**Not intended for commercial use.**


---

## 📅 Project Timeline

- **Week 1-2:** Data pipeline & Airflow setup ✅ **COMPLETE**
- **Week 2-3:** Drift monitoring implementation ✅ **COMPLETE**  
- **Week 3-4:** Model training & MLflow integration ✅ **COMPLETE**
- **Week 4:** API deployment & final polish ✅ **COMPLETE**
- **Week 4-5:** MLOps monitoring dashboard ✅ **COMPLETE**
- **Week 5:** Multi-repo deployment & integration ✅ **COMPLETE**
- **Presentation:** January 8th, 2026 🎯 **IN PROGRESS**

**Status:** 🎉 **PROJECT ALMOST COMPLETE** - All components in final stage of testing

---

<div align="center">

**Built with ❤️ by the CineMatch Team**

*Demonstrating modern MLOps practices for production-grade ML systems*

[⬆ Back to Top](#-cinematch---mlops-movie-recommendation-system)

</div>
