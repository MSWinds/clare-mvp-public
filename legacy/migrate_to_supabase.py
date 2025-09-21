"""
Database Migration Script: VPN Database → Supabase
Migrates chat_history, student_profiles, langchain_pg_collection, and langchain_pg_embedding tables to Supabase cloud database.
Handles JSONB and vector data type conversions. Skips tables that already exist with data.
"""

import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# Database connections
OLD_DB = os.getenv("DB_CONNECTION")  # VPN database
NEW_DB = os.getenv("DATABASE_URL")   # Supabase database

if not OLD_DB or not NEW_DB:
    print("Error: Both DB_CONNECTION and DATABASE_URL must be set in .env file")
    sys.exit(1)

# Tables to migrate
TABLES_TO_MIGRATE = [
    'chat_history',
    'student_profiles',
    'langchain_pg_collection',   # Collection metadata for PGVector
    'langchain_pg_embedding'     # Vector embeddings data
]

def test_connections():
    """Test both database connections"""
    print("Testing database connections...")

    try:
        # Test old database
        old_engine = create_engine(OLD_DB)
        with old_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ VPN database connection: OK")

        # Test new database
        new_engine = create_engine(NEW_DB)
        with new_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Supabase database connection: OK")

        return old_engine, new_engine

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        sys.exit(1)

def check_table_exists(engine, table_name):
    """Check if table exists in database"""
    try:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()
    except Exception as e:
        print(f"Error checking table {table_name}: {e}")
        return False

def get_table_info(engine, table_name):
    """Get table row count and sample data"""
    try:
        with engine.connect() as conn:
            # Get row count
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = count_result.scalar()

            # Get sample data (first 3 rows)
            sample_result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
            sample_data = sample_result.fetchall()

            return row_count, sample_data

    except Exception as e:
        print(f"Error getting info for {table_name}: {e}")
        return 0, []

def process_jsonb_columns(df, table_name):
    """Convert dict columns to JSON strings for PostgreSQL compatibility"""
    if table_name == 'student_profiles' and 'profile_summary' in df.columns:
        print(f"   Converting profile_summary JSONB data...")
        df['profile_summary'] = df['profile_summary'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x
        )
    elif table_name == 'langchain_pg_embedding' and 'cmetadata' in df.columns:
        print(f"   Converting cmetadata JSONB data...")
        df['cmetadata'] = df['cmetadata'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x
        )
    elif table_name == 'langchain_pg_collection' and 'cmetadata' in df.columns:
        print(f"   Converting collection cmetadata JSONB data...")
        df['cmetadata'] = df['cmetadata'].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x
        )
    return df

def handle_vector_columns(df, table_name):
    """Handle vector data types for langchain_pg_embedding"""
    if table_name == 'langchain_pg_embedding' and 'embedding' in df.columns:
        print(f"   Processing vector embedding data...")
        # Convert vector data to string representation for now
        # In production, you might want to preserve the actual vector format
        df['embedding'] = df['embedding'].astype(str)
    return df

def migrate_table(old_engine, new_engine, table_name):
    """Migrate a single table from old to new database"""
    print(f"\n📦 Migrating table: {table_name}")

    # Check if source table exists
    if not check_table_exists(old_engine, table_name):
        print(f"⚠️  Table {table_name} not found in source database")
        return False

    # Check if target table already exists and has data
    if check_table_exists(new_engine, table_name):
        target_row_count, _ = get_table_info(new_engine, table_name)
        if target_row_count > 0:
            print(f"✅ Table {table_name} already exists in target database with {target_row_count} rows - SKIPPING")
            return True

    # Get source table info
    row_count, sample_data = get_table_info(old_engine, table_name)
    print(f"   Source table has {row_count} rows")

    if row_count == 0:
        print(f"   Table {table_name} is empty, creating structure only")
        # For empty tables, we'll copy structure using pandas
        try:
            # Read empty structure
            df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", old_engine)
            df = process_jsonb_columns(df, table_name)
            df = handle_vector_columns(df, table_name)
            df.to_sql(table_name, new_engine, if_exists='replace', index=False)
            print(f"✅ Empty table structure created")
            return True
        except Exception as e:
            print(f"❌ Failed to create empty table structure: {e}")
            return False

    try:
        # For tables with data, migrate in chunks
        chunk_size = 1000 if row_count > 1000 else row_count

        print(f"   Migrating {row_count} rows in chunks of {chunk_size}...")

        # Read and write in chunks to handle large datasets
        for chunk_num, chunk_df in enumerate(pd.read_sql(
            f"SELECT * FROM {table_name}",
            old_engine,
            chunksize=chunk_size
        )):
            # Process special data types
            chunk_df = process_jsonb_columns(chunk_df, table_name)
            chunk_df = handle_vector_columns(chunk_df, table_name)
            
            # Write chunk to new database
            if_exists_mode = 'replace' if chunk_num == 0 else 'append'
            chunk_df.to_sql(table_name, new_engine, if_exists=if_exists_mode, index=False)

            rows_processed = (chunk_num + 1) * len(chunk_df)
            print(f"   Processed {min(rows_processed, row_count)}/{row_count} rows")

        # Verify migration
        new_row_count, _ = get_table_info(new_engine, table_name)

        if new_row_count == row_count:
            print(f"✅ Migration successful: {new_row_count} rows transferred")
            return True
        else:
            print(f"❌ Migration incomplete: {new_row_count}/{row_count} rows transferred")
            return False

    except Exception as e:
        print(f"❌ Migration failed for {table_name}: {e}")
        return False

def enable_pgvector_extension(engine):
    """Enable pgvector extension in Supabase"""
    print("\n🔧 Enabling pgvector extension...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        print("✅ pgvector extension enabled")
        return True
    except Exception as e:
        print(f"❌ Failed to enable pgvector: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 Starting Database Migration to Supabase")
    print("=" * 50)
    print(f"Source: VPN Database")
    print(f"Target: Supabase Database")
    print(f"Tables: {', '.join(TABLES_TO_MIGRATE)}")
    print("=" * 50)

    # Test connections
    old_engine, new_engine = test_connections()

    # Enable pgvector extension
    enable_pgvector_extension(new_engine)

    # Migration results
    results = {}

    # Migrate each table
    for table_name in TABLES_TO_MIGRATE:
        success = migrate_table(old_engine, new_engine, table_name)
        results[table_name] = success

    # Summary report
    print("\n" + "=" * 50)
    print("📊 MIGRATION SUMMARY")
    print("=" * 50)

    successful = sum(results.values())
    total = len(results)

    for table_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{table_name}: {status}")

    print(f"\nOverall: {successful}/{total} tables migrated successfully")

    if successful == total:
        print("\n🎉 Migration completed successfully!")
        print("You can now update your application to use DATABASE_URL")
    else:
        print(f"\n⚠️  Migration partially completed. {total - successful} tables failed.")
        print("Please check the errors above and retry if needed.")

    # Close connections
    old_engine.dispose()
    new_engine.dispose()

if __name__ == "__main__":
    # Add confirmation prompt for safety
    print("This will migrate data from your VPN database to Supabase.")
    print("Make sure you have:")
    print("1. VPN connection active")
    print("2. Both DB_CONNECTION and DATABASE_URL in .env")
    print("3. pgvector extension ready to be enabled")

    confirm = input("\nProceed with migration? (y/N): ").lower().strip()

    if confirm in ['y', 'yes']:
        main()
    else:
        print("Migration cancelled.")