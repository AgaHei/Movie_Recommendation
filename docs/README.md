# CineMatch Documentation

## 📖 Table of Contents

### Getting Started
- [Architecture Overview](mlops/architecture-diagram.md)
- [Project Setup Guide](README.md)

### Data Pipeline
- [Data Preparation](data/data-pipeline-overview.md)
- [Neon Database Schema](data/neon-schema.md)

### Airflow & Monitoring
- [Airflow Setup](airflow/01-airflow-setup.md)
- [Buffer Ingestion](airflow/02-buffer-ingestion.md)
- [Drift Monitoring](airflow/03-drift-monitoring.md)
- [Training Trigger](airflow/04-training-trigger.md)

### Model Training
- [Training Pipeline](models/training-guide.md)
- [MLflow Setup](models/mlflow-setup.md)

### Deployment
- [FastAPI Setup](api/fastapi-setup.md)
- [Docker Deployment](api/docker-guide.md)

### MLOps - Simulation Results
- [3-Week Drift Monitoring Log](mlops/weekly-simulation-log.md)
```
---

## **Documentation Structure:**
```
your-project/
├── README.md                              ← GitHub landing page
├── docs/
│   ├── README.md                          ← Docs navigation hub
│   │
│   │
│   ├── airflow/
│   │   ├── 01-airflow-setup.md           ← Docker, credentials
│   │   ├── 02-buffer-ingestion.md        ← How ingestion works
│   │   ├── 03-drift-monitoring.md        ← Drift detection guide
│   │   └── 04-training-trigger.md        ← TO BE ADDED (Next week)
│   │
│   ├── data/
│   │   ├── data-pipeline-overview.md     ← Dataset info, preprocessing
│   │   └── neon-schema.md                ← Database tables, design
│   │
│   ├── mlops/
│   │   ├── architecture-diagram.md       ← Full stack overview
│   │   └── weekly-simulation-log.md      ← The 3-week results!
│   │
│   ├── models/                            # TO BE ADDED
│   │   └── training-guide.md
│   │
│   ├── api/                               # TO BE ADDED
│   │   └── fastapi-setup.md
│   │
│   └── assets/
│       ├── screenshots/                   ← Airflow, Neon, etc.
│       └── diagrams/                      ← Architecture diagrams
│
├── airflow/
├── data/
├── models/
└── api/