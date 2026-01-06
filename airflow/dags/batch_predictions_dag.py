"""
DAG Batch Predictions - Détection de Model Drift
=================================================
Cette DAG :
1. Récupère un batch de données depuis ratings_buffer (via batch_id)
2. Fait des prédictions via l'API
3. Calcule les métriques (MAE, RMSE)
4. Déclenche le réentrainement si performance dégradée
5. Sauvegarde les prédictions dans la BDD

Déclenchée par buffer_ingestion_dag avec batch_id en configuration
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import pandas as pd
import requests
from sqlalchemy import create_engine
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════════════

default_args = {
    'owner': 'cinematch',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Configuration API
API_URL = "https://julienrouillard-movie-recommendation-api.hf.space"

# Seuils de performance (détection de drift)
EXPECTED_MAE = 0.79
EXPECTED_RMSE = 1.02
DEGRADATION_THRESHOLD = 0.10  # 10% de dégradation = réentrainement

# ══════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS HELPER
# ══════════════════════════════════════════════════════════════════════════════════════

def get_db_engine():
    """Crée et retourne un engine SQLAlchemy pour Neon"""
    neon_conn = os.getenv('NEON_CONNECTION_STRING')
    if not neon_conn:
        raise ValueError("NEON_CONNECTION_STRING n'est pas définie dans les variables d'environnement")
    return create_engine(neon_conn)


def load_batch_data(**context):
    """
    Charge les données du batch depuis ratings_buffer
    """
    print("\n" + "="*70)
    print("📥 CHARGEMENT DES DONNÉES DU BATCH")
    print("="*70)
    
    # Récupérer le batch_id depuis la config du DAG run
    batch_id = context['dag_run'].conf.get('batch_id') if context['dag_run'].conf else None
    
    if not batch_id:
        raise ValueError("batch_id manquant dans la configuration du DAG run")
    
    print(f"🎯 Batch ID: {batch_id}")
    
    # Connexion à la BDD
    engine = get_db_engine()
    
    # Charger les données du batch
    query = """
        SELECT "userId", "movieId", "rating", "timestamp", "batch_id"
        FROM ratings_buffer
        WHERE batch_id = %(batch_id)s
        ORDER BY timestamp
    """
    
    df = pd.read_sql(query, engine, params={'batch_id': batch_id})
    
    if len(df) == 0:
        print(f"⚠️  Aucune donnée trouvée pour batch_id={batch_id}")
        context['ti'].xcom_push(key='batch_id', value=batch_id)
        context['ti'].xcom_push(key='data_empty', value=True)
        return
    
    print(f"✅ {len(df):,} lignes chargées")
    print(f"   Users: {df['userId'].nunique()}")
    print(f"   Movies: {df['movieId'].nunique()}")
    print(f"   Rating moyen: {df['rating'].mean():.2f}")
    
    # Sauvegarder les données dans XCom
    context['ti'].xcom_push(key='batch_id', value=batch_id)
    context['ti'].xcom_push(key='batch_data', value=df.to_dict('records'))
    context['ti'].xcom_push(key='data_empty', value=False)
    
    print("="*70 + "\n")


def predict_batch(**context):
    """
    Appelle l'API pour faire des prédictions sur le batch (endpoint batch)
    """
    print("\n" + "="*70)
    print("🤖 PRÉDICTIONS VIA API (BATCH ENDPOINT)")
    print("="*70)
    
    # Vérifier si on a des données
    data_empty = context['ti'].xcom_pull(key='data_empty', task_ids='load_data')
    if data_empty:
        print("⚠️  Pas de données à prédire")
        context['ti'].xcom_push(key='predictions_empty', value=True)
        return
    
    # Récupérer les données
    batch_data = context['ti'].xcom_pull(key='batch_data', task_ids='load_data')
    df = pd.DataFrame(batch_data)
    
    print(f"📊 {len(df):,} prédictions à faire")
    print(f"🌐 API: {API_URL}/predict_batch")
    
    # Préparer les items pour l'appel batch
    items = [
        {"user_id": int(row['userId']), "movie_id": int(row['movieId'])}
        for _, row in df.iterrows()
    ]
    
    print(f"📦 Envoi de {len(items):,} items en batch...")
    
    try:
        # Appel API batch (un seul appel pour tout le batch !)
        response = requests.post(
            f"{API_URL}/predict_batch",
            json={"items": items},
            timeout=300  # 5 minutes de timeout pour les gros batches
        )
        
        if response.status_code == 200:
            api_predictions = response.json()['predictions']
            
            # Créer un dictionnaire pour mapper (userId, movieId) -> predicted_rating
            pred_map = {
                (pred['user_id'], pred['movie_id']): pred['rating']
                for pred in api_predictions
            }
            
            # Construire la liste finale avec actual_rating
            predictions = []
            for _, row in df.iterrows():
                user_id = int(row['userId'])
                movie_id = int(row['movieId'])
                predicted_rating = pred_map.get((user_id, movie_id))
                
                predictions.append({
                    'userId': user_id,
                    'movieId': movie_id,
                    'predicted_rating': predicted_rating,
                    'actual_rating': float(row['rating'])
                })
            
            success_count = len([p for p in predictions if p['predicted_rating'] is not None])
            error_count = len(predictions) - success_count
            
            print(f"\n✅ Prédictions terminées")
            print(f"   Succès: {success_count:,}")
            print(f"   Erreurs: {error_count:,}")
            
        else:
            print(f"❌ Erreur API: {response.status_code}")
            print(f"   Response: {response.text}")
            predictions = []
            
    except Exception as e:
        print(f"❌ Exception lors de l'appel API batch: {e}")
        predictions = []
    
    # Sauvegarder les prédictions
    context['ti'].xcom_push(key='predictions', value=predictions)
    context['ti'].xcom_push(key='predictions_empty', value=(len(predictions) == 0))
    
    print("="*70 + "\n")


def calculate_metrics(**context):
    """
    Calcule les métriques MAE et RMSE pour détecter le drift
    """
    print("\n" + "="*70)
    print("📊 CALCUL DES MÉTRIQUES (DÉTECTION DRIFT)")
    print("="*70)
    
    # Vérifier si on a des prédictions
    predictions_empty = context['ti'].xcom_pull(key='predictions_empty', task_ids='predict')
    if predictions_empty:
        print("⚠️  Pas de prédictions à évaluer")
        context['ti'].xcom_push(key='drift_detected', value=False)
        return
    
    # Récupérer les prédictions
    predictions = context['ti'].xcom_pull(key='predictions', task_ids='predict')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    n = len(predictions)
    print(f"🔍 Évaluation de {n:,} prédictions (batch={batch_id})")
    
    # Calcul MAE et RMSE
    errors = [abs(p['predicted_rating'] - p['actual_rating']) for p in predictions]
    squared_errors = [(p['predicted_rating'] - p['actual_rating'])**2 for p in predictions]
    
    mae = np.mean(errors)
    rmse = np.sqrt(np.mean(squared_errors))
    
    print(f"\n📈 Métriques actuelles:")
    print(f"   MAE:  {mae:.4f}")
    print(f"   RMSE: {rmse:.4f}")
    
    print(f"\n📍 Baseline attendue:")
    print(f"   MAE:  {EXPECTED_MAE:.4f}")
    print(f"   RMSE: {EXPECTED_RMSE:.4f}")
    
    # Calcul de la dégradation
    mae_degradation = (mae / EXPECTED_MAE - 1) * 100
    rmse_degradation = (rmse / EXPECTED_RMSE - 1) * 100
    
    print(f"\n🔬 Dégradation:")
    print(f"   MAE:  {mae_degradation:+.2f}%")
    print(f"   RMSE: {rmse_degradation:+.2f}%")
    print(f"   Seuil: {DEGRADATION_THRESHOLD*100:.0f}%")
    
    # Détection du drift
    mae_drift = mae > EXPECTED_MAE * (1 + DEGRADATION_THRESHOLD)
    rmse_drift = rmse > EXPECTED_RMSE * (1 + DEGRADATION_THRESHOLD)
    drift_detected = mae_drift or rmse_drift
    
    print(f"\n{'🚨 DRIFT DÉTECTÉ!' if drift_detected else '✅ Pas de drift'}")
    
    if drift_detected:
        print(f"   {'MAE' if mae_drift else ''} {'RMSE' if rmse_drift else ''} dépasse le seuil")
        print(f"   ⚡ Le réentrainement sera déclenché")
    else:
        print(f"   Performance stable, pas de réentrainement nécessaire")
    
    # Sauvegarder les résultats
    context['ti'].xcom_push(key='mae', value=mae)
    context['ti'].xcom_push(key='rmse', value=rmse)
    context['ti'].xcom_push(key='drift_detected', value=bool(drift_detected))
    
    print("="*70 + "\n")


def save_predictions(**context):
    """
    Sauvegarde les prédictions dans la BDD (optimisé avec batch updates)
    """
    print("\n" + "="*70)
    print("💾 SAUVEGARDE DES PRÉDICTIONS DANS LA BDD (OPTIMISÉ)")
    print("="*70)
    
    # Vérifier si on a des prédictions
    predictions_empty = context['ti'].xcom_pull(key='predictions_empty', task_ids='predict')
    if predictions_empty:
        print("⚠️  Pas de prédictions à sauvegarder")
        return
    
    # Récupérer les prédictions
    predictions = context['ti'].xcom_pull(key='predictions', task_ids='predict')
    batch_id = context['ti'].xcom_pull(key='batch_id', task_ids='load_data')
    
    # Filtrer les prédictions valides (non-None)
    valid_predictions = [p for p in predictions if p['predicted_rating'] is not None]
    
    print(f"💾 Sauvegarde de {len(valid_predictions):,} prédictions (batch={batch_id})")
    
    if len(valid_predictions) == 0:
        print("⚠️  Aucune prédiction valide à sauvegarder")
        return
    
    # Connexion à la BDD
    engine = get_db_engine()
    
    # Créer un DataFrame avec les prédictions
    pred_df = pd.DataFrame(valid_predictions)
    
    # Créer une table temporaire avec les prédictions
    with engine.begin() as conn:
        # Créer une table temp
        conn.execute("""
            CREATE TEMP TABLE IF NOT EXISTS temp_predictions (
                "userId" INT,
                "movieId" INT,
                predicted_rating FLOAT,
                batch_id TEXT
            )
        """)
        
        # Insérer toutes les prédictions dans la table temp
        pred_df[['userId', 'movieId', 'predicted_rating']].to_sql(
            'temp_predictions',
            conn,
            if_exists='append',
            index=False,
            method='multi'
        )
        
        # Ajouter le batch_id
        conn.execute(f"""
            UPDATE temp_predictions SET batch_id = '{batch_id}'
        """)
        
        # Faire le update en masse depuis la table temp vers ratings_buffer
        result = conn.execute("""
            UPDATE ratings_buffer rb
            SET predicted_rating = tp.predicted_rating
            FROM temp_predictions tp
            WHERE rb."userId" = tp."userId"
              AND rb."movieId" = tp."movieId"
              AND rb.batch_id = tp.batch_id
        """)
        
        updated = result.rowcount
    
    print(f"✅ {updated:,} lignes mises à jour dans ratings_buffer")
    print("="*70 + "\n")


def decide_retraining(**context):
    """
    Décide si on déclenche le réentrainement ou pas (branching)
    """
    print("\n" + "="*70)
    print("🔍 CHECKING IF RETRAINING NEEDED")
    print("="*70 + "\n")
    
    drift_detected = context['ti'].xcom_pull(key='drift_detected', task_ids='calculate_metrics')
    
    print(f"🔎 Valeur récupérée de XCom: drift_detected = {drift_detected}")
    print(f"🔎 Type: {type(drift_detected)}")
    
    if drift_detected:
        print("🔥 Drift détecté → Déclenchement du réentrainement")
        return 'trigger_test_retraining'
    else:
        print("✅ Pas de drift → Pas de réentrainement")
        return 'skip_retraining'


# ══════════════════════════════════════════════════════════════════════════════════════
# DAG
# ══════════════════════════════════════════════════════════════════════════════════════

with DAG(
    'batch_predictions',
    default_args=default_args,
    description='Batch predictions + détection de drift + trigger réentrainement',
    schedule_interval=None,  # Déclenché par buffer_ingestion_dag
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['batch', 'predictions', 'drift', 'cinematch'],
) as dag:
    
    # Tâche 1: Charger les données du batch
    load_data = PythonOperator(
        task_id='load_data',
        python_callable=load_batch_data,
    )
    
    # Tâche 2: Faire les prédictions via API
    predict = PythonOperator(
        task_id='predict',
        python_callable=predict_batch,
    )
    
    # Tâche 3: Calculer les métriques
    calculate_metrics_task = PythonOperator(
        task_id='calculate_metrics',
        python_callable=calculate_metrics,
    )
    
    # Tâche 4: Sauvegarder les prédictions dans la BDD
    save_predictions_task = PythonOperator(
        task_id='save_predictions',
        python_callable=save_predictions,
    )
    
    # Tâche 5: Décider si on réentraine (branching)
    decide = BranchPythonOperator(
        task_id='decide_retraining',
        python_callable=decide_retraining,
    )
    
    # Tâche 6a: Déclencher le réentrainement (les tests)
    trigger_test_retraining = TriggerDagRunOperator(
        task_id='trigger_test_retraining',
        trigger_dag_id='ci_docker_build_test',
        wait_for_completion=False,
    )
    
    # Tâche 6b: Ne rien faire (pas de réentrainement)
    skip_retraining = EmptyOperator(
        task_id='skip_retraining',
    )
    
    # Tâche 7: Fin (pour reconverger les branches)
    end = EmptyOperator(
        task_id='end',
        trigger_rule='none_failed_min_one_success',
    )
    
    # ══════════════════════════════════════════════════════════════════════════════════════
    # DÉPENDANCES
    # ══════════════════════════════════════════════════════════════════════════════════════
    
    load_data >> predict >> calculate_metrics_task >> save_predictions_task >> decide
    decide >> [trigger_test_retraining, skip_retraining]
    [trigger_test_retraining, skip_retraining] >> end