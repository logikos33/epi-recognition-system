#!/usr/bin/env python3
"""
Script to run the cameras table migration on Railway
"""

import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        sys.exit(1)

    print(f"🔗 Connecting to database: {database_url.split('@')[1]}")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Read migration SQL
        migration_path = os.path.join(os.path.dirname(__file__), '002_create_cameras_table.sql')
        with open(migration_path, 'r') as f:
            sql_content = f.read()

        # Execute migration
        with engine.connect() as conn:
            print("🔄 Running cameras table migration...")
            conn.execute(text(sql_content))
            conn.commit()
            print("✅ Migration completed successfully!")

            # Verify table exists
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'cameras'"))
            if result.fetchone():
                print("✅ Table 'cameras' verified!")

                # Show table structure
                print("\n📊 Table structure:")
                result = conn.execute(text("\d cameras"))
                for row in result:
                    print(f"  {row}")

            else:
                print("❌ Table 'cameras' not found!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()