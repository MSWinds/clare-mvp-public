#!/usr/bin/env python3
"""
Database Migration Runner
Safely executes the profile_summary VARCHAR -> JSON migration
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def run_migration():
    """Execute the database migration with proper error handling"""
    
    # Load environment variables
    load_dotenv()
    connection_string = os.getenv("DB_CONNECTION")
    
    if not connection_string:
        print("❌ Error: DB_CONNECTION environment variable not set")
        print("   Make sure your .env file contains the database connection string")
        return False
    
    try:
        # Create database engine
        engine = create_engine(connection_string)
        print("✅ Database connection established")
        
        # Read migration SQL
        with open('database_migration.sql', 'r') as f:
            sql_content = f.read()
        
        # Split commands by semicolon and clean them up
        commands = []
        raw_commands = sql_content.split(';')
        
        for raw_cmd in raw_commands:
            # Remove comments and empty lines
            lines = []
            for line in raw_cmd.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    lines.append(line)
            
            # Join the cleaned lines
            cmd = ' '.join(lines).strip()
            
            # Only add non-empty commands
            if cmd:
                commands.append(cmd)
        
        print(f"📋 Migration commands found:")
        for i, cmd in enumerate(commands, 1):
            preview = cmd[:60] + "..." if len(cmd) > 60 else cmd
            print(f"  [{i}] {preview}")
        
        print(f"📋 Found {len(commands)} migration commands to execute")
        
        # Execute migration in a transaction
        with engine.begin() as conn:
            print("\n🔄 Starting migration...")
            
            for i, cmd in enumerate(commands, 1):
                try:
                    print(f"[{i}/{len(commands)}] Executing: {cmd[:50]}{'...' if len(cmd) > 50 else ''}")
                    conn.execute(text(cmd))
                    print(f"  ✅ Success")
                except Exception as cmd_error:
                    print(f"  ❌ Failed: {cmd_error}")
                    raise  # Re-raise to rollback transaction
            
            print("\n🎉 Migration completed successfully!")
            
            # Verify the migration worked
            print("\n🔍 Verifying migration...")
            
            # Check new table structure
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'student_profiles' AND column_name = 'profile_summary'
            """)).fetchone()
            
            if result:
                print(f"✅ New table column 'profile_summary' type: {result.data_type}")
                if 'jsonb' in result.data_type.lower():
                    print("✅ New table verification successful - column is JSONB")
                else:
                    print(f"⚠️  Warning: Expected JSONB, found {result.data_type}")
            else:
                print("❌ Could not verify new table - column not found")
            
            # Check legacy table exists
            legacy_check = conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'student_profiles_legacy'
            """)).fetchone()
            
            if legacy_check and legacy_check.count > 0:
                print("✅ Legacy table 'student_profiles_legacy' preserved")
            else:
                print("⚠️  Legacy table not found (may not have existed)")
            
            # Check data migration
            new_count = conn.execute(text("SELECT COUNT(*) as count FROM student_profiles")).fetchone()
            legacy_count = conn.execute(text("""
                SELECT COUNT(*) as count FROM student_profiles_legacy 
                WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'student_profiles_legacy')
            """)).fetchone()
            
            print(f"📊 Data migration summary:")
            print(f"   Legacy table records: {legacy_count.count if legacy_count else 0}")
            print(f"   New table records: {new_count.count if new_count else 0}")
            
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("   The transaction has been rolled back - no changes were made")
        return False

if __name__ == "__main__":
    print("🗃️  Database Migration Runner")
    print("=" * 40)
    
    # Check if migration file exists
    if not os.path.exists('database_migration.sql'):
        print("❌ Error: database_migration.sql not found in current directory")
        exit(1)
    
    # Run the migration
    success = run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("   Your student_profiles table now uses JSONB for profile_summary")
        print("   You can now run the profile analyzer system")
    else:
        print("\n❌ Migration failed!")
        print("   Please check the error messages above and try again")
        exit(1)