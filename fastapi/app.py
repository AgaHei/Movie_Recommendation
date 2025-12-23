# ══════════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════ DEPENDENCIES ════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
from dotenv import load_dotenv
import mlflow
import pickle
import os
import numpy as np
from pydantic import BaseModel
from mlflow.tracking import MlflowClient
from sqlalchemy import create_engine
import pandas as pd
from enum import Enum


# ══════════════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════ CONFIGURATION ════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

# Load environment variables
load_dotenv()

# MLflow configuration
MLFLOW_TRACKING_URI = "https://julienrouillard-mlflow-movie-recommandation.hf.space"
MODEL_NAME = "movie_recommendation_hybrid_system"
MODEL_VERSION = 1

# Database configuration
DB_URL = os.getenv("DB_URL", "postgresql://neondb_owner:npg_s5NhbHAIkE3W@ep-square-truth-agcbtrap.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require")

# Global variables
pipeline = None
movies_df = None


# ══════════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════ API SETUP ═══════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="🎬 Movie Recommendation API",
    description="""
# 🎯 Hybrid Movie Recommendation System

This API provides **personalized movie recommendations** by combining collaborative filtering 
and content-based approaches into a powerful hybrid model.

---

## 🏗️ System Architecture

### 1️⃣ Collaborative Filtering (SVD)
- **Algorithm**: Truncated Singular Value Decomposition  
- **Latent Dimensions**: 500 components
- **Purpose**: Captures hidden patterns in user rating behaviors
- **Strength**: Discovers implicit preferences without knowing movie content
- **Training**: User-item matrix factorization on 1M+ ratings

### 2️⃣ Content-Based Filtering (Genome Embeddings)
- **Source**: MovieLens Genome Tags (1,128 semantic tags per movie)
- **Dimensionality Reduction**: PCA to 128 dimensions
- **Purpose**: Understands movie characteristics and themes
- **Strength**: Provides recommendations even for new users or movies
- **Coverage**: 13k+ movies with rich genome embeddings

### 3️⃣ Hybrid Model (Final Layer)
- **Algorithm**: Stochastic Gradient Descent Regressor
- **Input Features**: SVD prediction + 128D Genome embeddings (129 total features)
- **Output**: Final rating prediction (0.5 - 5.0 stars)
- **Performance**: 
  - **RMSE**: ~1.02 on test set
  - **MAE**: ~0.79
  - **Improvement**: 3.2% over SVD baseline

---

## 🔮 Prediction Strategies

The system intelligently adapts its prediction strategy based on available data:

| Strategy | Scenario | Components Used | Accuracy |
|----------|----------|----------------|----------|
| 🌟 **Hybrid Full** | User + Movie both known, genome available | SVD + Genome + Hybrid Model | ⭐⭐⭐⭐⭐ Best |
| 🆕 **Hybrid New Movie** | User known, new movie with genome | User mean + Genome + Hybrid Model | ⭐⭐⭐⭐ Great |
| 👤 **Hybrid New User** | New user, movie known with genome | Movie mean + Genome + Hybrid Model | ⭐⭐⭐⭐ Great |
| 📊 **SVD Only** | User + Movie both known, no genome | Pure collaborative filtering (SVD) | ⭐⭐⭐ Good |
| 🎲 **Fallback Mean** | Cold start, minimal data | Movie or global average | ⭐⭐ Fair |

---

## 📊 Training Dataset

- **Total Ratings**: 1,000,000 interactions
- **Users**: 6.7k+ unique users
- **Movies**: 62k+ films in catalog
- **Training Set**: 800k ratings (80% temporal split)
- **Test Set**: 200k ratings (20% temporal split)
- **Genome Coverage**: 13k+ movies with semantic tags
- **Rating Scale**: 0.5 to 5.0 stars (half-star increments)
- **Sparsity**: ~99.5% (realistic user-movie matrix)

---

## 🎯 API Endpoints

### 🔢 Predict Rating
**`POST /predict`** 

Get a predicted rating for a specific user-movie pair.
- **Use Case**: "Will user X like movie Y?"
- **Input**: User ID, Movie ID
- **Output**: Predicted rating


### 🏆 Top 50 Personalized Recommendations
**`POST /predict_top_of_top`**

Get personalized Top 50 movies from the 1000 highest-rated films.
- **Use Case**: "What are the best movies for this user?"
- **Input**: User ID
- **Output**: 50 personalized recommendations from top-rated films


### 🎭 Top 10 by Genre
**`POST /predict_top_of_genre`** 

Get personalized Top 10 movies within a specific genre.
- **Use Case**: "What are the best Action movies for this user?"
- **Input**: User ID, Genre
- **Output**: 10 personalized recommendations in chosen genre

---

## 🚀 Key Features

✅ **Cold Start Handling**: Works for new users and new movies  
✅ **Multi-Strategy**: Automatically selects best prediction approach  
✅ **High Performance**: Sub-second response times  
✅ **Scalable**: Handles 162K+ users and 62K+ movies  
✅ **Production-Ready**: Deployed with MLflow model registry  


---

    """,
    version="1.0.0"
)


# ══════════════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════ STARTUP ═══════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def load_model():
    """Load model from MLflow Model Registry and movies data from Neon"""
    global pipeline, movies_df
    
    print("🔄 Loading model from MLflow Model Registry...")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Version: {MODEL_VERSION}")
    
    try:
        # Set MLflow tracking URI
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Get the model version from registry
        client = MlflowClient()
        
        model_version = client.get_model_version(
            name=MODEL_NAME,
            version=MODEL_VERSION
        )
        
        # Get the source run
        run_id = model_version.run_id
        print(f"   - Source run_id: {run_id}")
        
        # Download artifacts from the source run
        artifact_path = client.download_artifacts(run_id, "pipeline.pkl")
        
        # Load the pipeline
        with open(artifact_path, 'rb') as f:
            pipeline = pickle.load(f)
        
        print("✅ Model loaded successfully!")
        print(f"   - Users: {len(pipeline['user_to_idx']):,}")
        print(f"   - Movies: {len(pipeline['movie_to_idx']):,}")
        print(f"   - Movies with genome: {len(pipeline['movie_embeddings_dict']):,}")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise
    
    # Load movies data from Neon
    print("\n🔄 Loading movies data from Neon database...")
    try:
        engine = create_engine(DB_URL)
        
        # Get all columns except genome embeddings
        movies_query = """
        SELECT * FROM movies
        """
        movies_df_full = pd.read_sql(movies_query, engine)
        
        # Keep only movieId, title, and genre columns
        genre_columns = [col for col in movies_df_full.columns 
                        if col not in ['movieId', 'title', '(no genres listed)'] 
                        and not col.startswith('g_emb_')]
        
        movies_df = movies_df_full[['movieId', 'title'] + genre_columns]
        
        print("✅ Movies data loaded successfully!")
        print(f"   - Total movies in DB: {len(movies_df):,}")
        print(f"   - Genre columns: {genre_columns}")
        
    except Exception as e:
        print(f"❌ Error loading movies data: {e}")
        raise


# ══════════════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════ PYDANTIC MODELS ═══════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

class PredictRequest(BaseModel):
    user_id: int
    movie_id: int


class TopOfTopRequest(BaseModel):
    user_id: int


class Genre(str, Enum):
    ACTION = "Action"
    ADVENTURE = "Adventure"
    ANIMATION = "Animation"
    CHILDREN = "Children"
    COMEDY = "Comedy"
    CRIME = "Crime"
    DOCUMENTARY = "Documentary"
    DRAMA = "Drama"
    FANTASY = "Fantasy"
    FILM_NOIR = "Film-Noir"
    HORROR = "Horror"
    IMAX = "IMAX"
    MUSICAL = "Musical"
    MYSTERY = "Mystery"
    ROMANCE = "Romance"
    SCI_FI = "Sci-Fi"
    THRILLER = "Thriller"
    WAR = "War"
    WESTERN = "Western"


class TopOfGenreRequest(BaseModel):
    user_id: int
    genre: Genre


# ══════════════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════ PREDICTION LOGIC ════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

def predict_rating(user_id: int, movie_id: int) -> float:
    """
    Predict rating for a user-movie pair using hybrid strategy
    """
    # Extract components from pipeline
    user_to_idx = pipeline['user_to_idx']
    movie_to_idx = pipeline['movie_to_idx']
    user_factors = pipeline['user_factors']
    movie_factors = pipeline['movie_factors']
    user_means = pipeline['user_means']
    movie_means = pipeline['movie_means']
    global_mean_rating = pipeline['global_mean_rating']
    movie_embeddings_dict = pipeline['movie_embeddings_dict']
    hybrid_model = pipeline['hybrid_model']
    hybrid_scaler = pipeline['hybrid_scaler']
    
    # Check what data is available
    user_idx = user_to_idx.get(user_id)
    movie_idx = movie_to_idx.get(movie_id)
    has_embedding = movie_id in movie_embeddings_dict
    
    # Strategy 1: Hybrid full (both known, has embedding)
    if user_idx is not None and movie_idx is not None and has_embedding:
        svd_pred = np.dot(user_factors[user_idx], movie_factors[movie_idx]) + user_means[user_idx]
        movie_emb = movie_embeddings_dict[movie_id]
        features = np.hstack([[svd_pred], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return float(np.clip(pred, 0.5, 5.0))
    
    # Strategy 2: Hybrid new movie (user known, movie new but has embedding)
    if user_idx is not None and movie_idx is None and has_embedding:
        svd_pred = user_means[user_idx]
        movie_emb = movie_embeddings_dict[movie_id]
        features = np.hstack([[svd_pred], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return float(np.clip(pred, 0.5, 5.0))
    
    # Strategy 3: Hybrid new user (user new, movie known with embedding)
    if user_idx is None and movie_idx is not None and has_embedding:
        movie_mean = movie_means.get(movie_id, global_mean_rating)
        movie_emb = movie_embeddings_dict[movie_id]
        features = np.hstack([[movie_mean], movie_emb]).reshape(1, -1)
        features_scaled = hybrid_scaler.transform(features)
        pred = hybrid_model.predict(features_scaled)[0]
        return float(np.clip(pred, 0.5, 5.0))
    
    # Strategy 4: SVD only (both known, no embedding)
    if user_idx is not None and movie_idx is not None:
        svd_pred = np.dot(user_factors[user_idx], movie_factors[movie_idx]) + user_means[user_idx]
        return float(np.clip(svd_pred, 0.5, 5.0))
    
    # Strategy 5: Fallback - movie mean or global mean
    if movie_id in movie_means:
        return float(movie_means[movie_id])
    else:
        return float(global_mean_rating)
    


def get_top_of_top_recommendations(user_id: int, n_top: int = 50) -> list:
    """
    Get personalized top N recommendations from the 1000 highest-rated movies
    """
    movie_means = pipeline['movie_means']
    
    # Get top 1000 movies by average rating
    top_1000_movies = sorted(movie_means.items(), key=lambda x: x[1], reverse=True)[:1000]
    top_1000_movie_ids = [movie_id for movie_id, _ in top_1000_movies]
    
    # Predict ratings for these movies for the user
    predictions = []
    for movie_id in top_1000_movie_ids:
        predicted_rating = predict_rating(user_id, movie_id)
        predictions.append({
            'movieId': movie_id,
            'predicted_rating': predicted_rating
        })
    
    # Sort by predicted rating (descending)
    predictions_sorted = sorted(predictions, key=lambda x: x['predicted_rating'], reverse=True)
    
    # Get top N
    top_n_predictions = predictions_sorted[:n_top]
    
    # Merge with movie titles
    result = []
    for pred in top_n_predictions:
        movie_id = pred['movieId']
        movie_info = movies_df[movies_df['movieId'] == movie_id]
        if not movie_info.empty:
            result.append({
                'movieId': int(movie_id),
                'title': movie_info.iloc[0]['title']
            })
    
    return result


def get_top_of_genre_recommendations(user_id: int, genre: str, n_top: int = 10) -> dict:
    """
    Get personalized top N recommendations from the best movies of a specific genre
    """
    # Filter movies by genre
    genre_movies = movies_df[movies_df[genre] == 1]
    
    # Check if genre has movies
    if genre_movies.empty:
        return {"error": f"No movies found for genre: {genre}"}
    
    # Get movie IDs for this genre
    genre_movie_ids = genre_movies['movieId'].tolist()
    
    # Get ratings for these movies from movie_means
    movie_means = pipeline['movie_means']
    genre_movies_with_ratings = [
        (movie_id, movie_means.get(movie_id, 0)) 
        for movie_id in genre_movie_ids 
        if movie_id in movie_means
    ]
    
    # Sort by rating and take top 1000 (or less if fewer available)
    top_genre_movies = sorted(genre_movies_with_ratings, key=lambda x: x[1], reverse=True)[:1000]
    top_genre_movie_ids = [movie_id for movie_id, _ in top_genre_movies]
    
    # Check if we have movies after filtering
    if not top_genre_movie_ids:
        return {"error": f"No rated movies found for genre: {genre}"}
    
    # Predict ratings for these movies for the user
    predictions = []
    for movie_id in top_genre_movie_ids:
        predicted_rating = predict_rating(user_id, movie_id)
        predictions.append({
            'movieId': movie_id,
            'predicted_rating': predicted_rating
        })
    
    # Sort by predicted rating (descending)
    predictions_sorted = sorted(predictions, key=lambda x: x['predicted_rating'], reverse=True)
    
    # Get top N
    top_n_predictions = predictions_sorted[:n_top]
    
    # Merge with movie titles
    result = []
    for pred in top_n_predictions:
        movie_id = pred['movieId']
        movie_info = movies_df[movies_df['movieId'] == movie_id]
        if not movie_info.empty:
            result.append({
                'movieId': int(movie_id),
                'title': movie_info.iloc[0]['title'],
                'genre': genre
            })
    
    return {"recommendations": result}


# ══════════════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════ ENDPOINTS ══════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════════════

@app.post("/predict")
async def predict(request: PredictRequest):
    """
    Predict rating for a user-movie pair
    
    Predict the rating a user would give to a specific movie.
    
    **The system uses a hybrid approach:**
    - Hybrid Full: When both user and movie are known with genome data (best accuracy)
    - Hybrid New Movie: When user is known but movie is new (uses genome embeddings)
    - Hybrid New User: When user is new but movie is known (uses movie characteristics)
    - SVD Only: When both are known but no genome data available
    - Fallback: Returns movie average or global average for cold start
    
    **Parameters:**
    - user_id (int): The unique identifier of the user
    - movie_id (int): The unique identifier of the movie
    
    **Returns:**
    - rating (float): Predicted rating on a scale from 0.5 to 5.0 stars
    """
    rating = predict_rating(request.user_id, request.movie_id)
    return {"rating": rating}


@app.post("/predict_top_of_top")
async def predict_top_of_top(request: TopOfTopRequest):
    """
    Get Top 50 personalized recommendations from best-rated movies
    
    Get personalized Top 50 movie recommendations from the 1000 globally highest-rated films.
    
    **Process:**
    1. Identifies the 1000 movies with highest average ratings across all users
    2. Predicts how the specific user would rate each of these 1000 movies
    3. Returns the top 50 movies with highest personalized predicted ratings
    
    This endpoint is ideal for discovering acclaimed films tailored to user preferences.
    
    **Parameters:**
    - user_id (int): The unique identifier of the user
    
    **Returns:**
    - recommendations (list): Array of 50 movie objects, each containing movieId (int) and title (str)
    
    Results are sorted by predicted rating in descending order (best matches first).
    """
    recommendations = get_top_of_top_recommendations(request.user_id, n_top=50)
    return {"recommendations": recommendations}


@app.post("/predict_top_of_genre")
async def predict_top_of_genre(request: TopOfGenreRequest):
    """
    Get Top 10 personalized recommendations within a specific genre
    
    Get personalized Top 10 movie recommendations from the best-rated films of a chosen genre.
    
    **Process:**
    1. Filters movies by the selected genre
    2. Identifies up to 1000 highest-rated movies in that genre
    3. Predicts how the user would rate each of these movies
    4. Returns the top 10 movies with highest personalized predicted ratings
    
    This endpoint is ideal for discovering the best films in a specific genre tailored to user taste.
    
    **Parameters:**
    - user_id (int): The unique identifier of the user
    - genre (Genre): The movie genre (Action, Comedy, Drama, Sci-Fi, etc.)
    
    **Returns:**
    - recommendations (list): Array of up to 10 movie objects, each containing movieId (int), title (str), and genre (str)
    - error (str): Error message if no movies found for the genre
    
    Results are sorted by predicted rating in descending order (best matches first).
    
    Available genres: Action, Adventure, Animation, Children, Comedy, Crime, Documentary, Drama, 
    Fantasy, Film-Noir, Horror, IMAX, Musical, Mystery, Romance, Sci-Fi, Thriller, War, Western
    """
    result = get_top_of_genre_recommendations(request.user_id, request.genre.value, n_top=10)
    return result