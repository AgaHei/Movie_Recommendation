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
- [Project Structure](#-project-structure)
- [Results](#-results)
- [Team](#-team)
- [Documentation](#-documentation)
- [Acknowledgments](#-acknowledgments)

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
- Continuous monitoring simulating 3 weeks of production operation
- Automated retraining triggered by data drift
- Complete CI/CD/CT/CM pipeline
- Free-tier infrastructure (€0 budget)

**Please note that this project is a team work in active progress so frequent changes will be introduced to this repository.**
---

## ✨ Key Features

### 🔍 Intelligent Drift Detection
- **Statistical Tests:** Kolmogorov-Smirnov, mean change, variance analysis
- **Threshold-Based Decisions:** Configurable sensitivity for production needs
- **Progressive Monitoring:** Accumulates evidence over time before triggering retraining
- **Complete Audit Trail:** Every decision logged to database

### 🔄 Automated Continuous Training
- **GitHub Actions Integration:** Triggered automatically when drift detected
- **MLflow Experiment Tracking:** All training runs versioned and comparable
- **Model Registry:** Automatic promotion of improved models to production
- **Performance Monitoring:** RMSE, MAE, Precision@K tracked over time

### 🚀 Production Deployment
- **FastAPI REST API:** Modern, fast, auto-documented endpoints
- **Docker Containerization:** Reproducible deployment anywhere
- **Cloud Hosting:** Deployed on Render/Railway (free tier)
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

Data Layer                Orchestration              Training & Deployment
    │                          │                              │
    ▼                          ▼                              ▼
┌─────────┐             ┌──────────────┐            ┌─────────────────┐
│  Neon   │◀───────────▶│   Airflow   │───────────▶│ GitHub Action  │
│  (DB)   │             │   (Docker)   │            │  (CI/CD/CT)     │
│         │             │              │            │                 │
│ • Data  │             │ • Ingestion  │            │ • Training      │
│ • Meta  │             │ • Monitoring │            │ • Evaluation    │
│ • Logs  │             │ • Triggers   │            │ • Deployment    │
└─────────┘             └──────────────┘            └────────┬────────┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │     MLflow       │
                                                    │  (Experiments)   │
                                                    └────────┬─────────┘
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
- **Hosting:** Render / Railway (free tier)
- **CI/CD:** GitHub Actions

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose** (for Airflow)
- **Python 3.11+** (for local development)
- **Git** (for version control)
- **Neon Account** (free tier: [neon.tech](https://neon.tech))

### Installation

```bash
# 1. Clone the repository
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

---

## 📁 Project Structure

```
cinematch/
├── README.md                          ← You are here!
├── .github/
│   └── workflows/
│       ├── model_training.yml         ← CI/CD for training
│       └── deploy_api.yml             ← Deployment automation
│
├── airflow/                           ← Orchestration
│   ├── dags/
│   │   ├── buffer_ingestion_dag.py   ← Data loading
│   │   ├── drift_monitoring_dag.py   ← Drift detection
│   │   └── trigger_retraining_dag.py ← Training trigger
│   ├── docker-compose.yml
│   └── .env.example
│
├── data/                              ← Data pipeline
│   ├── raw/                           ← Original MovieLens
│   ├── prepared/                      ← Processed datasets
│   │   ├── ratings_initial_ml.parquet
│   │   └── buffer_batches/
│   └── ingestion_scripts/
│       └── load_academic_dataset.py
│
├── models/                            ← ML training
│   ├── train_model.py                ← Training script
│   ├── evaluate.py                   ← Model evaluation
│   └── requirements.txt
│
├── api/                               ← Deployment
│   ├── main.py                       ← FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
│
└── docs/                              ← Documentation
    ├── README.md                      ← Docs navigation
    ├── airflow/
    │   ├── 01-airflow-setup.md
    │   ├── 02-buffer-ingestion.md
    │   └── 03-drift-monitoring.md
    ├── data/
    │   ├── data-pipeline-overview.md
    │   └── neon-schema.md
    └── mlops/
        ├── architecture-diagram.md
        └── weekly-simulation-log.md
```

---

## 📊 Results

### 3-Week Drift Monitoring Simulation

Our simulation demonstrated progressive drift detection over 3 weeks:

| Week | Buffer Size | KS Statistic | Mean Change | Decision |
|------|-------------|--------------|-------------|----------|
| **1** | 500k ratings | 0.0176 | +0.97% | ✅ No drift - Continue |
| **2** | 1M ratings | --- | ---| ⚠️ Potential early signals |
| **3** | 1.5M ratings | --- | --- | 🚨 Potential DRIFT Retrain |

### Model Performance Improvement

After retraining with accumulated buffer data:

| Metric | Baseline Model | Retrained Model | Improvement |
|--------|----------------|-----------------|-------------|
| **RMSE** | --- | ---| ---  |
| **MAE** | --- | --- | --- |
| **Precision@10** | --- | --- | ---|
| **Training Data** | 700k | --- | ---|

**Key Achievement:** Automated system detected drift and triggered retraining, resulting in measurable model improvement!

**[📈 Detailed Results & Analysis](docs/mlops/weekly-simulation-log.md)**

---

## 👥 Team

**Jedha Data Science & Engineering Bootcamp - Final Project (December 2025)**

### Team Members

| Name | Role | Responsibilities |
|------|------|------------------|
| **[Agnès]** | Data Pipeline & Monitoring | Airflow orchestration, drift detection, data engineering, Neon database design |
| **[Julien]** | Model Training & Experimentation | Collaborative filtering models, MLflow integration, hyperparameter tuning |
| **[Matéo]** | Deployment & API | FastAPI development, Docker containerization, cloud deployment |

### Collaboration

- **Version Control:** Git + GitHub
- **Project Management:** GitHub Projects / Trello
- **Communication:** Discord
- **Documentation:** Markdown in `/docs`

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

## 🎓 Learning Outcomes

This project demonstrates skills in:

### MLOps Practices
✅ **Continuous Integration (CI)** - Automated code testing  
✅ **Continuous Deployment (CD)** - Automated model deployment  
✅ **Continuous Training (CT)** - Drift-triggered retraining  
✅ **Continuous Monitoring (CM)** - Statistical drift detection  

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
✅ **GitHub Actions** - CI/CD automation  

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
- **Dagshub** - [dagshub.com](https://dagshub.com/)


### Bootcamp
**Jedha Bootcamp** - Data Science & Engineering Lead Bootcamp
Special thanks to our instructors for guidance throughout the project!

---

## 📝 License

This project is an academic work created for the Jedha Bootcamp final project (December 2025 - January 2026).  
**Not intended for commercial use.**


---

## 📅 Project Timeline

- **Week 1-2:** Data pipeline & Airflow setup
- **Week 2-3:** Drift monitoring implementation
- **Week 3-4:** Model training & MLflow integration
- **Week 4:** API deployment & final polish
- **Presentation:** [Date TBD]

**Status:** 🚧 In Progress - Data Pipeline Complete ✅

---

<div align="center">

**Built with ❤️ by the CineMatch Team**

*Demonstrating modern MLOps practices for production-grade ML systems*

[⬆ Back to Top](#-cinematch---mlops-movie-recommendation-system)

</div>
