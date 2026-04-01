#!/usr/bin/env python3
"""
Create training tables manually.
Run with: source venv/bin/activate && python create_training_tables.py
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from backend.database import SessionLocal

def create_tables():
    """Create training_jobs and trained_models tables."""
    try:
        db = SessionLocal()

        print("Creating training_jobs table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS training_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                preset VARCHAR(20) NOT NULL,
                model_size VARCHAR(10) NOT NULL,
                epochs INTEGER NOT NULL,
                dataset_yaml_path VARCHAR(500),
                model_output_path VARCHAR(500),
                progress INTEGER DEFAULT 0,
                current_epoch INTEGER DEFAULT 0,
                metrics JSONB,
                error_message TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("✅ training_jobs table created")

        print("Creating trained_models table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS trained_models (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                job_id UUID REFERENCES training_jobs(id) ON DELETE SET NULL,
                name VARCHAR(255) NOT NULL,
                model_path VARCHAR(500) NOT NULL,
                model_size VARCHAR(10) NOT NULL,
                is_active BOOLEAN DEFAULT FALSE,
                metrics JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("✅ trained_models table created")

        print("Creating indexes...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_training_jobs_user_id ON training_jobs(user_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_training_jobs_created_at ON training_jobs(created_at DESC)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trained_models_user_id ON trained_models(user_id)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_trained_models_is_active ON trained_models(is_active)
            WHERE is_active = TRUE
        """))
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_trained_models_user_active
            ON trained_models(user_id) WHERE is_active = TRUE
        """))
        print("✅ Indexes created")

        db.commit()
        print("\n✅ All training tables created successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == '__main__':
    create_tables()
