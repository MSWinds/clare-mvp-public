#!/usr/bin/env python3
"""
Simple database connection test script
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv not available, using environment variables directly")

def test_database_connection():
    """Test database connection with detailed error reporting"""

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False

    print(f"🔍 Testing connection to: {database_url[:50]}...")

    try:
        from sqlalchemy import create_engine, text

        # Create engine with timeout settings
        engine = create_engine(
            database_url,
            pool_timeout=10,
            connect_args={"connect_timeout": 15}
        )

        print("⚙️  Engine created successfully")

        # Test basic connection
        with engine.connect() as conn:
            print("✅ Database connection established!")

            # Test simple query
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Simple query successful: {row}")

            # Test timestamp
            result = conn.execute(text("SELECT NOW() as current_time"))
            row = result.fetchone()
            print(f"✅ Timestamp query: {row}")

            # Test if our tables exist
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('chat_history', 'student_profiles')
            """))
            tables = result.fetchall()
            print(f"📋 Found tables: {[t[0] for t in tables]}")

        print("🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"📝 Error details: {str(e)}")

        # Additional error analysis
        error_str = str(e).lower()
        if "timeout" in error_str:
            print("🕐 This appears to be a timeout issue")
        elif "connection refused" in error_str:
            print("🚫 Connection refused - server may be down")
        elif "host" in error_str:
            print("🌐 DNS/hostname resolution issue")

        return False

if __name__ == "__main__":
    print(f"🚀 Database Connection Test - {datetime.now()}")
    print("=" * 50)

    success = test_database_connection()

    print("=" * 50)
    if success:
        print("✅ Connection test PASSED")
    else:
        print("❌ Connection test FAILED")

    sys.exit(0 if success else 1)