from dotenv import load_dotenv
load_dotenv()

# Dependencies
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from pathlib import Path
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import SGDRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tqdm import tqdm
import time
import psycopg2
from sqlalchemy import create_engine
import pickle
import os

# MLflow configuration
MLFLOW_TRACKING_URI = "https://julienrouillard-mlflow-movie-recommandation.hf.space"
EXPERIMENT_NAME = "movie_recommendation_system"

# Database configuration
DB_URL = os.getenv("DB_URL", "postgresql://neondb_owner:npg_s5NhbHAIkE3W@ep-square-truth-agcbtrap.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require")

print("=" * 60)
print("MOVIE RECOMMENDATION SYSTEM - MLFLOW TRAINING")
print("=" * 60)

def load_data_from_neon(db_url):
    """Load ratings and movies data from Neon database"""
    print("\n📥 Loading data from Neon database...")
    
    engine = create_engine(db_url)
    
    # Load ratings
    print("  - Loading ratings...")
    ratings_query = """
    SELECT "userId", "movieId", "rating", "timestamp"
    FROM ratings
    ORDER BY "timestamp"
    """
    ratings = pd.read_sql(ratings_query, engine)
    
    # Load movies  
    print("  - Loading movies...")
    movies_query = """
    SELECT "movieId", "title"
    FROM movies
    """
    movies = pd.read_sql(movies_query, engine)
    
    print(f"\n✅ Data loaded:")
    print(f"  - Ratings: {len(ratings):,} rows")
    print(f"  - Movies: {len(movies):,} rows")
    print(f"  - Users: {ratings['userId'].nunique():,} unique")
    
    return ratings, movies


def temporal_split(ratings, test_ratio=0.20):
    """Split data temporally for evaluation"""
    print("\n⏰ Creating temporal train/test split for evaluation...")
    
    # Sort by timestamp
    ratings = ratings.sort_values('timestamp').reset_index(drop=True)
    
    # Calculate split index
    n_total = len(ratings)
    n_train = int(n_total * (1 - test_ratio))
    
    # Create splits
    train_ratings = ratings.iloc[:n_train].copy()
    test_ratings = ratings.iloc[n_train:].copy()
    
    print(f"  - Train: {len(train_ratings):,} ({(1-test_ratio)*100:.0f}%)")
    print(f"  - Test: {len(test_ratings):,} ({test_ratio*100:.0f}%)")
    
    return train_ratings, test_ratings


def create_mappings(train_ratings):
    """Create user and movie ID mappings from train set"""
    print("\n🔢 Creating user/movie mappings...")
    
    # Get unique users and movies from TRAIN set only
    unique_users = train_ratings['userId'].unique()
    unique_movies = train_ratings['movieId'].unique()
    
    # Create bidirectional mappings
    user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
    idx_to_user = {idx: user_id for user_id, idx in user_to_idx.items()}
    
    movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(unique_movies)}
    idx_to_movie = {idx: movie_id for movie_id, idx in movie_to_idx.items()}
    
    print(f"  - Users: {len(user_to_idx):,}")
    print(f"  - Movies: {len(movie_to_idx):,}")
    
    return user_to_idx, idx_to_user, movie_to_idx, idx_to_movie


def create_sparse_matrix(train_ratings, user_to_idx, movie_to_idx):
    """Create sparse user-item matrix and calculate statistics"""
    print("\n🔨 Building sparse matrix and statistics...")
    
    # Add mapped indices
    train_ratings['user_idx'] = train_ratings['userId'].map(user_to_idx)
    train_ratings['movie_idx'] = train_ratings['movieId'].map(movie_to_idx)
    
    # Extract data for sparse matrix
    user_indices = train_ratings['user_idx'].values
    movie_indices = train_ratings['movie_idx'].values
    ratings_values = train_ratings['rating'].values
    
    # Create sparse matrix
    n_users = len(user_to_idx)
    n_movies = len(movie_to_idx)
    
    user_item_matrix = csr_matrix(
        (ratings_values, (user_indices, movie_indices)),
        shape=(n_users, n_movies)
    )
    
    # Calculate statistics
    global_mean_rating = train_ratings['rating'].mean()
    
    # User means (for SVD centering)
    user_means = np.array([
        user_item_matrix.getrow(i).data.mean() if user_item_matrix.getrow(i).nnz > 0 
        else global_mean_rating
        for i in range(n_users)
    ])
    
    # Movie means (for cold start)
    movie_means = train_ratings.groupby('movieId')['rating'].mean().to_dict()
    
    print(f"  - Matrix shape: {user_item_matrix.shape}")
    print(f"  - Sparsity: {(1 - user_item_matrix.nnz / (n_users * n_movies)) * 100:.2f}%")
    print(f"  - Global mean: {global_mean_rating:.3f}")
    
    return user_item_matrix, global_mean_rating, user_means, movie_means


def train_svd_model(user_item_matrix, user_means, n_components=500):
    """Train SVD collaborative filtering model"""
    print(f"\n🧠 Training SVD model (n_components={n_components})...")
    
    # Center the matrix (subtract user means)
    print("  - Centering matrix...")
    user_item_centered = user_item_matrix.copy()
    for user_idx in range(len(user_means)):
        start_idx = user_item_matrix.indptr[user_idx]
        end_idx = user_item_matrix.indptr[user_idx + 1]
        user_item_centered.data[start_idx:end_idx] -= user_means[user_idx]
    
    # Train SVD
    start_time = time.time()
    
    svd_model = TruncatedSVD(
        n_components=n_components,
        random_state=42,
        algorithm='randomized'
    )
    
    user_factors = svd_model.fit_transform(user_item_centered)
    movie_factors = svd_model.components_.T
    
    training_time = time.time() - start_time
    explained_var = svd_model.explained_variance_ratio_.sum()
    
    print(f"  ✅ Trained in {training_time:.2f}s")
    print(f"  - Explained variance: {explained_var:.4f} ({explained_var*100:.2f}%)")
    
    return svd_model, user_factors, movie_factors, training_time


def create_genome_embeddings(n_components_pca=128):
    """Load genome data and create movie embeddings with PCA"""
    print(f"\n🧬 Creating genome embeddings (PCA n_components={n_components_pca})...")
    
    # Load genome data
    print("  - Loading genome scores from CSV...")
    genome_scores = pd.read_csv("raw/genome-scores.csv")
    
    # Reshape to wide format (movies × tags)
    print("  - Reshaping to wide format...")
    genome_wide = genome_scores.pivot(index='movieId', columns='tagId', values='relevance')
    genome_wide = genome_wide.fillna(0)
    
    print(f"    Shape: {genome_wide.shape} (movies x tags)")
    
    # Standardize features
    print("  - Standardizing features...")
    scaler = StandardScaler()
    genome_scaled = scaler.fit_transform(genome_wide)
    
    # Apply PCA
    print(f"  - Applying PCA ({n_components_pca} dimensions)...")
    pca = PCA(n_components=n_components_pca, random_state=42)
    genome_embeddings = pca.fit_transform(genome_scaled)
    
    explained_var = pca.explained_variance_ratio_.sum()
    print(f"  ✅ PCA complete")
    print(f"    - Explained variance: {explained_var:.4f} ({explained_var*100:.2f}%)")
    
    # Create embeddings dictionary
    movie_embeddings_dict = {
        movie_id: genome_embeddings[idx]
        for idx, movie_id in enumerate(genome_wide.index)
    }
    
    print(f"    - Movies with embeddings: {len(movie_embeddings_dict):,}")
    
    return movie_embeddings_dict, pca, scaler


def build_hybrid_dataset(train_ratings, user_factors, movie_factors, user_means, 
                         user_to_idx, movie_to_idx, movie_embeddings_dict):
    """Build hybrid training dataset: SVD predictions + movie embeddings"""
    print("\n🏗️ Building hybrid training dataset...")
    
    # Filter: keep only movies with genome embeddings
    train_with_genome = train_ratings[
        train_ratings['movieId'].isin(movie_embeddings_dict.keys())
    ].copy()
    
    print(f"  - Original train: {len(train_ratings):,}")
    print(f"  - With genome: {len(train_with_genome):,} ({len(train_with_genome)/len(train_ratings)*100:.1f}%)")

    # Mapper avec les vrais indices
    print("  - Mapping indices...")
    train_with_genome['user_idx'] = train_with_genome['userId'].map(user_to_idx)
    train_with_genome['movie_idx'] = train_with_genome['movieId'].map(movie_to_idx)

    # Delete lines with NaN
    train_with_genome = train_with_genome.dropna(subset=['user_idx', 'movie_idx'])

    # Convert as int
    train_with_genome['user_idx'] = train_with_genome['user_idx'].astype(int)
    train_with_genome['movie_idx'] = train_with_genome['movie_idx'].astype(int)

    print(f"  - After mapping: {len(train_with_genome):,}")

    # Generate SVD predictions
    print("  - Generating SVD predictions...")
    svd_predictions = []
    movie_embeddings = []
    
    for idx, row in tqdm(train_with_genome.iterrows(), total=len(train_with_genome), desc="  Processing"):
        user_idx = int(row['user_idx'])  # ← Ajouter int()
        movie_idx = int(row['movie_idx'])  # ← Ajouter int()
        
        # SVD prediction
        svd_pred = np.dot(user_factors[user_idx], movie_factors[movie_idx]) + user_means[user_idx]
        svd_predictions.append(svd_pred)
        
        # Movie embedding
        movie_emb = movie_embeddings_dict[row['movieId']]
        movie_embeddings.append(movie_emb)
    
    # Build feature matrix: [svd_pred, movie_embedding_128_dims]
    svd_predictions = np.array(svd_predictions).reshape(-1, 1)
    movie_embeddings = np.array(movie_embeddings)
    
    X_hybrid = np.hstack([svd_predictions, movie_embeddings])
    y_hybrid = train_with_genome['rating'].values
    
    print(f"\n  ✅ Hybrid dataset created:")
    print(f"    - Shape: {X_hybrid.shape}")
    print(f"    - Features: SVD pred (1) + Movie embeddings ({movie_embeddings.shape[1]})")
    print(f"    - Samples: {len(y_hybrid):,}")
    
    return X_hybrid, y_hybrid


def train_hybrid_model(X_hybrid, y_hybrid, n_epochs=5, learning_rate='optimal', alpha=0.01):
    """Train hybrid SGD Regressor model"""
    print(f"\n🧠 Training Hybrid model (SGDRegressor)...")
    print(f"  - Training samples: {len(X_hybrid):,}")
    
    # Fit scaler on sample
    print("  - Fitting scaler...")
    sample_size = min(100000, len(X_hybrid))
    scaler = StandardScaler()
    scaler.fit(X_hybrid[:sample_size])
    
    # Initialize model
    hybrid_model = SGDRegressor(
        learning_rate=learning_rate,
        eta0=0.001,
        penalty='l2',
        alpha=alpha,
        random_state=42
    )
    
    # Train by batches
    batch_size = 50000
    n_batches = (len(X_hybrid) // batch_size) + 1
    start_time = time.time()
    
    for epoch in range(n_epochs):
        print(f"\n  📍 Epoch {epoch + 1}/{n_epochs}")
        indices = np.random.permutation(len(X_hybrid))
        
        for i in tqdm(range(n_batches), desc="    Batches"):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(X_hybrid))
            batch_indices = indices[start_idx:end_idx]
            
            X_batch = scaler.transform(X_hybrid[batch_indices])
            y_batch = y_hybrid[batch_indices]
            
            hybrid_model.partial_fit(X_batch, y_batch)
    
    training_time = time.time() - start_time
    print(f"\n  ✅ Training complete in {training_time:.2f}s")
    
    return hybrid_model, scaler, training_time


def predict_final(user_id, movie_id, user_to_idx, movie_to_idx, user_factors, 
                  movie_factors, user_means, movie_embeddings_dict, movie_means,
                  global_mean_rating, hybrid_model, hybrid_scaler):
    """
    Multi-strategy prediction system:
    1. Hybrid (both known)
    2. Hybrid (new movie with user SVD)
    3. Hybrid (new user with movie mean + embedding)
    4. SVD (no genome)
    5. Fallback (mean)
    """
    
    user_idx = user_to_idx.get(user_id)
    movie_idx = movie_to_idx.get(movie_id)
    has_embedding = movie_id in movie_embeddings_dict
    
    # Strategy 1: Hybrid full (both known + has embedding)
    if user_idx is not None and movie_idx is not None and has_embedding:
        # SVD prediction
        svd_pred = np.dot(user_factors[user_idx], movie_factors[movie_idx]) + user_means[user_idx]
        # Movie embedding
        movie_emb = movie_embeddings_dict[movie_id]
        # Hybrid prediction
        features = np.hstack([[svd_pred], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return np.clip(pred, 0.5, 5.0), 'hybrid_full'
    
    # Strategy 2: Hybrid new movie (user known, movie new but has embedding)
    if user_idx is not None and movie_idx is None and has_embedding:
        # Use user mean as SVD prediction
        svd_pred = user_means[user_idx]
        movie_emb = movie_embeddings_dict[movie_id]
        features = np.hstack([[svd_pred], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return np.clip(pred, 0.5, 5.0), 'hybrid_new_movie'
    
    # Strategy 3: Hybrid new user (user new, movie known with embedding)
    if user_idx is None and movie_idx is not None and has_embedding:
        # Use movie mean as SVD prediction
        movie_mean = movie_means.get(movie_id, global_mean_rating)
        movie_emb = movie_embeddings_dict[movie_id]
        features = np.hstack([[movie_mean], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return np.clip(pred, 0.5, 5.0), 'hybrid_new_user'
    
    # Strategy 4: SVD only (both known, no embedding)
    if user_idx is not None and movie_idx is not None:
        svd_pred = np.dot(user_factors[user_idx], movie_factors[movie_idx]) + user_means[user_idx]
        return np.clip(svd_pred, 0.5, 5.0), 'svd_no_genome'
    
    # Strategy 5: Fallback - movie mean or global mean
    if movie_id in movie_means:
        return movie_means[movie_id], 'fallback_movie_mean'
    else:
        return global_mean_rating, 'fallback_global_mean'
    

def evaluate_on_test(test_ratings, user_to_idx, movie_to_idx, user_factors,
                     movie_factors, user_means, movie_embeddings_dict, movie_means,
                     global_mean_rating, hybrid_model, hybrid_scaler):
    """Evaluate the complete system on test set"""
    print("\n🔮 Evaluating on test set...")
    
    # Add mappings to test set
    test_ratings['user_idx'] = test_ratings['userId'].map(user_to_idx)
    test_ratings['movie_idx'] = test_ratings['movieId'].map(movie_to_idx)
    
    predictions = []
    strategies = []
    
    for idx, row in tqdm(test_ratings.iterrows(), total=len(test_ratings), desc="  Predicting"):
        pred, strategy = predict_final(
            row['userId'], 
            row['movieId'],
            user_to_idx,
            movie_to_idx,
            user_factors,
            movie_factors,
            user_means,
            movie_embeddings_dict,
            movie_means,
            global_mean_rating,
            hybrid_model,
            hybrid_scaler
        )
        predictions.append(pred)
        strategies.append(strategy)
    
    predictions = np.array(predictions)
    actuals = test_ratings['rating'].values
    
    # Calculate metrics
    test_rmse = np.sqrt(mean_squared_error(actuals, predictions))
    test_mae = mean_absolute_error(actuals, predictions)
    
    # Strategy breakdown
    from collections import Counter
    strategy_counts = Counter(strategies)
    
    print(f"\n📈 Test Set Metrics:")
    print(f"  - RMSE: {test_rmse:.4f}")
    print(f"  - MAE: {test_mae:.4f}")
    
    print(f"\n📊 Strategy Usage:")
    for strategy, count in strategy_counts.items():
        pct = count / len(strategies) * 100
        print(f"  - {strategy}: {count:,} ({pct:.1f}%)")
    
    return test_rmse, test_mae, strategy_counts


def main(n_components_svd=500, n_components_pca=128, n_epochs_hybrid=5, 
         learning_rate='optimal', alpha=0.01):
    """Main training pipeline with MLflow logging"""
    
    # Configure MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    with mlflow.start_run(run_name="hybrid_recommendation_system_v1"):
        
        # Log hyperparameters
        mlflow.log_param("n_components_svd", n_components_svd)
        mlflow.log_param("n_components_pca", n_components_pca)
        mlflow.log_param("n_epochs_hybrid", n_epochs_hybrid)
        mlflow.log_param("learning_rate", learning_rate)
        mlflow.log_param("alpha", alpha)
        
        # 1. Load data
        ratings, movies = load_data_from_neon(DB_URL)
        mlflow.log_param("total_ratings", len(ratings))
        mlflow.log_param("total_users", ratings['userId'].nunique())
        mlflow.log_param("total_movies", len(movies))
        
        # 2. Split train/test
        train_ratings, test_ratings = temporal_split(ratings, test_ratio=0.20)
        mlflow.log_param("train_size", len(train_ratings))
        mlflow.log_param("test_size", len(test_ratings))
        
        # 3. Create mappings
        user_to_idx, idx_to_user, movie_to_idx, idx_to_movie = create_mappings(train_ratings)
        
        # 4. Create sparse matrix and statistics
        user_item_matrix, global_mean_rating, user_means, movie_means = create_sparse_matrix(
            train_ratings, user_to_idx, movie_to_idx
        )
        mlflow.log_metric("global_mean_rating", global_mean_rating)
        
        # 5. Train SVD
        svd_model, user_factors, movie_factors, svd_time = train_svd_model(
            user_item_matrix, user_means, n_components=n_components_svd
        )
        mlflow.log_metric("svd_explained_variance", svd_model.explained_variance_ratio_.sum())
        
        # 6. Create genome embeddings
        movie_embeddings_dict, pca, genome_scaler = create_genome_embeddings(
            n_components_pca=n_components_pca
        )
        
        # 7. Build hybrid dataset
        X_hybrid, y_hybrid = build_hybrid_dataset(
            train_ratings, user_factors, movie_factors, user_means, user_to_idx,
            movie_to_idx, movie_embeddings_dict
        )
        
        # 8. Train hybrid model
        hybrid_model, hybrid_scaler, hybrid_time = train_hybrid_model(
            X_hybrid, y_hybrid, n_epochs=n_epochs_hybrid, 
            learning_rate=learning_rate, alpha=alpha
        )
        mlflow.log_metric("hybrid_training_time", hybrid_time)
        
        # 9. Evaluate on test set
        test_rmse, test_mae, strategy_counts = evaluate_on_test(
            test_ratings, user_to_idx, movie_to_idx, user_factors,
            movie_factors, user_means, movie_embeddings_dict, movie_means,
            global_mean_rating, hybrid_model, hybrid_scaler
        )
        mlflow.log_metric("test_rmse", test_rmse)
        mlflow.log_metric("test_mae", test_mae)
        
        # Log strategy distribution
        for strategy, count in strategy_counts.items():
            mlflow.log_metric(f"strategy_{strategy}", count)
        
        # 10. Save complete pipeline
        print("\n💾 Saving pipeline artifacts...")
        pipeline = {
            'user_to_idx': user_to_idx,
            'movie_to_idx': movie_to_idx,
            'user_factors': user_factors,
            'movie_factors': movie_factors,
            'user_means': user_means,
            'movie_means': movie_means,
            'global_mean_rating': global_mean_rating,
            'movie_embeddings_dict': movie_embeddings_dict,
            'hybrid_model': hybrid_model,
            'hybrid_scaler': hybrid_scaler,
            'svd_model': svd_model,
            'genome_pca': pca,
            'genome_scaler': genome_scaler
        }

        # Save locally then log to MLflow
        with open('pipeline.pkl', 'wb') as f:
            pickle.dump(pipeline, f)
        
        mlflow.log_artifact('pipeline.pkl')

        # Register in Model Registry
        run_id = mlflow.active_run().info.run_id
        mlflow.register_model(
            model_uri=f"runs:/{run_id}/pipeline.pkl",
            name="movie_recommendation_hybrid_system"
        )
        print("  ✅ Model registered in Model Registry as 'movie_recommendation_hybrid_system'")

        # Clean up local file
        os.remove('pipeline.pkl')
        print("  - Local file cleaned up")
        
        print("\n✅ Training complete!")
        print(f"  - Test RMSE: {test_rmse:.4f}")
        print(f"  - Test MAE: {test_mae:.4f}")
        print(f"  - MLflow run: {mlflow.active_run().info.run_id}")


if __name__ == "__main__":
    main()