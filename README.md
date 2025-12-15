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
data/
├── notebooks/
│   ├── 01_EDA_MovieLens_25M.ipynb          # Exploratory data analysis
│   └── 02_Data_Preparation_MovieLens_25M.ipynb  # Data preparation & feature engineering
├── raw/                                      # Raw MovieLens 25M data files (not tracked)
├── prepared/                                 # Processed data artifacts (not tracked)
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

## 🚀 Getting Started

### Prerequisites

- Python 3.12+ (tested with Python 3.12.10)
- pip package manager
- Virtual environment tool (venv)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AgaHei/Movie_Recommendation.git
   cd data
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS/Linux
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download MovieLens 25M dataset**
   
   Option A: Manual download
   - Visit: https://grouplens.org/datasets/movielens/25m/
   - Download `ml-25m.zip` (~265 MB)
   - Extract to `raw/` directory
   
   Option B: Automated download script
   ```bash
   # Run this Python script to download and extract the dataset
   python scripts/download_dataset.py
   ```
   
   **Note**: The `raw/` folder is excluded from Git (see `.gitignore`). Each team member must download the data independently.

### Running the Notebooks

1. **Start Jupyter**
   ```bash
   jupyter notebook
   ```

2. **Run notebooks in order**:
   - `01_EDA_MovieLens_25M.ipynb` - Explore the dataset
   - `02_Data_Preparation_MovieLens_25M.ipynb` - Prepare data for ML models

## 📥 Data Management

### For Team Members

Since data files are excluded from Git (`.gitignore`), each team member must set up their local data:

**Step 1: Download the dataset**

Using the automated script (recommended):
```bash
python scripts/download_dataset.py
```

Or manually:
1. Visit: https://grouplens.org/datasets/movielens/25m/
2. Download `ml-25m.zip` (~265 MB)
3. Extract to `raw/` directory

**Step 2: Generate processed artifacts**

Once you have the raw data, run the preparation notebook to generate the `prepared/` folder:
```bash
jupyter notebook notebooks/02_Data_Preparation_MovieLens_25M.ipynb
```

This creates the necessary Parquet files for model training (~2.6 GB, generated locally).

### Data Workflow

```
1. Clone repository
   ↓
2. Download raw data (raw/ folder)
   ↓
3. Run preparation notebook
   ↓
4. Generated prepared/ folder locally
   ↓
5. Train ML models using prepared/ data
```

**Note**: `raw/` and `prepared/` folders are in `.gitignore` - they're never committed to Git.

## 📊 Key Features

### Data Preparation
- **Memory-efficient processing**: Handles 25M+ rows without OOM errors
- **Feature engineering**: 
  - Genre one-hot encoding
  - PCA dimensionality reduction (1,128 → 64 genome tag embeddings)
  - Temporal features extraction
- **Temporal splitting**: 70% train / 20% test / 10% buffer (chronological)

### Artifacts Generated
After running the preparation notebook, the following files are created in `prepared/`:

- `ratings_train.parquet` (~1.5 GB) - Training interactions
- `ratings_test.parquet` (~430 MB) - Test interactions
- `ratings_buffer.parquet` (~215 MB) - Continuous monitoring buffer
- `movie_features_small.parquet` (~500 MB) - Compact movie features with PCA embeddings
- `movie_features_uni.parquet` - Full movie features (reference only)
- `movie_embeddings.parquet` - PCA genome embeddings (reference only)

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

- **Python 3.12**
- **pandas** - Data manipulation
- **NumPy** - Numerical computing
- **scikit-learn** - Machine learning & PCA
- **matplotlib & seaborn** - Visualization
- **PyArrow** - Efficient Parquet I/O

## 📝 Next Steps
1. **Baseline Model**: Train SVD/ALS collaborative filtering
2. **Hybrid Model**: Integrate movie embeddings with collaborative signals
3. **Evaluation**: Compare models on test set using RMSE, MAE, Precision@K
4. **Monitoring**: Detect drift using buffer data
5. **Deployment**: Build API for real-time recommendations

## 🚀 Project Roadmap & Team Coordination

### Phase 1: Data Pipeline (✅ In Progress - Agnès)
- [x] EDA and dataset exploration
- [x] Data preparation and feature engineering
- [x] Dimensionality reduction (PCA)
- [x] Temporal splitting (train/test/buffer)
- [ ] Data documentation and quality metrics

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

**For external contributors**:
- Please open an issue to discuss proposed changes
- Follow the existing code style and structure
- Test thoroughly before submitting PRs

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
