from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
engine = create_engine(os.getenv("NEON_CONNECTION_STRING"))

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM ratings"))
    count = result.scalar()
    print(f"✅ Ratings table has {count:,} rows")
    
    # Also check splits
    result_train = conn.execute(text("SELECT COUNT(*) FROM ratings WHERE data_split = 'train'"))
    result_test = conn.execute(text("SELECT COUNT(*) FROM ratings WHERE data_split = 'test'"))
    print(f"   - Training: {result_train.scalar():,} rows")
    print(f"   - Test: {result_test.scalar():,} rows")
