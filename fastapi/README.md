---
title: Movie Recommendation API
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# 🎬 Movie Recommendation API

Hybrid movie recommendation system combining collaborative filtering (SVD) and content-based filtering (Genome Embeddings).
```

**3. Vérifie ton `requirements.txt` (il doit contenir) :**
```
fastapi
uvicorn[standard]
mlflow==2.10.2
python-dotenv
pandas
numpy
scikit-learn
scipy
boto3
sqlalchemy
psycopg2-binary