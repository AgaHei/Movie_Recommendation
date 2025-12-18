# Apache Airflow - MovieLens Recommendation System

This folder contains the Apache Airflow orchestration setup for the MovieLens recommendation system project.

##  Structure

```
airflow/
 dags/                    # Airflow DAG definitions (workflow scripts)
 logs/                    # Airflow execution logs (auto-generated, not tracked)
 plugins/                 # Custom Airflow plugins (not tracked)
 docker-compose.yml       # Docker services configuration
 Dockerfile              # Custom Airflow image definition
 requirements.txt        # Python packages for Airflow workers
 .env                    # Environment variables (not tracked - create from .env.example)
 .env.example            # Template for environment configuration
```

##  Getting Started

### Prerequisites
- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** (usually included with Docker Desktop)

### Initial Setup

1. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with your credentials**:
   - Add your Neon PostgreSQL connection string
   - Update MLflow URI when available

3. **Build and start Airflow**:
   ```bash
   docker-compose up -d
   ```

   This will:
   - Build a custom Airflow image with project dependencies
   - Initialize the Airflow metadata database
   - Start the webserver and scheduler

4. **Access the Airflow UI**:
   - URL: http://localhost:8080
   - Username: `airflow`
   - Password: `airflow`

### Managing Airflow

```bash
# Start Airflow (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop Airflow
docker-compose down

# Rebuild after changing requirements.txt or Dockerfile
docker-compose build
docker-compose up -d

# Execute commands in Airflow container
docker-compose exec airflow-webserver bash
```

##  Custom Dependencies

The Airflow workers include these additional Python packages (see `requirements.txt`):
- `pandas` - Data manipulation
- `pyarrow` - Parquet file handling
- `scipy` - Statistical analysis
- `requests` - HTTP requests
- `python-dotenv` - Environment variable management

**Note**: SQLAlchemy, psycopg2-binary, and MLflow are already included in the base Airflow image.

##  Configuration

### Environment Variables
Set in `.env` file:
- `NEON_CONNECTION_STRING`: Your Neon PostgreSQL connection string
- `MLFLOW_TRACKING_URI`: MLflow tracking server URL
- `_AIRFLOW_WWW_USER_USERNAME`: Web UI username (default: airflow)
- `_AIRFLOW_WWW_USER_PASSWORD`: Web UI password (default: airflow)

### Docker Services
- **airflow-webserver**: Web UI and API (port 8080)
- **airflow-scheduler**: Task scheduling and orchestration
- **postgres**: Airflow metadata database (port 5432)

##  DAGs (Workflows)

*Coming soon* - DAGs will be added to the `dags/` folder:

1. **Batch Ingestion DAG**: Weekly ingestion of rating buffers to Neon
2. **Model Training DAG**: Periodic model retraining
3. **Drift Detection DAG**: Monitor data quality and distribution changes
4. **Model Deployment DAG**: Deploy trained models to production

##  Troubleshooting

### Issue: Containers won't start
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker-compose logs

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Issue: Port 8080 already in use
Edit `docker-compose.yml` and change the port mapping:
```yaml
ports:
  - "8081:8080"  # Use 8081 instead
```

### Issue: Permission denied errors
On Linux/Mac, you may need to set the correct user ID:
```bash
echo "AIRFLOW_UID=utf8(id -u)" >> .env
docker-compose up -d
```

##  Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow Docker Setup](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [Writing DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)

---

**Last Updated**: December 2025  
**Airflow Version**: 2.8.1  
**Python Version**: 3.11
