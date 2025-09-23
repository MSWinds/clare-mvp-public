"""
Weekly Profile Updates Script
Manual script to simulate weekly automated profile updates aligned with class schedule.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.workflows.profile_analyzer import analyze_and_update_profile
import json

connection_string = os.getenv("DATABASE_URL")
if not connection_string:
    raise ValueError("DATABASE_URL environment variable not set.")

engine = create_engine(connection_string)

def get_students_with_recent_activity(days: int = 7) -> list[str]:
    query = text("""
        SELECT DISTINCT student_id, COUNT(*) as interaction_count
        FROM chat_history 
        WHERE timestamp >= :since_date
        GROUP BY student_id
        HAVING COUNT(*) >= 3
        ORDER BY interaction_count DESC
    """)
    
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    try:
        with engine.connect() as conn:
            results = conn.execute(query, {"since_date": since_date}).fetchall()
        
        students = [row.student_id for row in results]
        print(f"Found {len(students)} students with activity in last {days} days")
        return students
        
    except Exception as e:
        print(f"Error querying active students: {e}")
        return []

def get_students_needing_profile_update(days: int = 7) -> list[str]:
    query = text("""
        WITH recent_activity AS (
            SELECT DISTINCT student_id
            FROM chat_history 
            WHERE timestamp >= :activity_since
        ),
        recent_profiles AS (
            SELECT DISTINCT student_id
            FROM student_profiles 
            WHERE timestamp >= :profile_since
        )
        SELECT ra.student_id
        FROM recent_activity ra
        LEFT JOIN recent_profiles rp ON ra.student_id = rp.student_id
        WHERE rp.student_id IS NULL
    """)
    
    activity_since = datetime.now(timezone.utc) - timedelta(days=days)
    profile_since = datetime.now(timezone.utc) - timedelta(days=days//2)
    
    try:
        with engine.connect() as conn:
            results = conn.execute(query, {
                "activity_since": activity_since,
                "profile_since": profile_since
            }).fetchall()
        
        students = [row.student_id for row in results]
        print(f"Found {len(students)} students needing profile updates")
        return students
        
    except Exception as e:
        print(f"Error querying students needing updates: {e}")
        return []

async def run_weekly_profile_updates(target_students: list[str] = None, force_update: bool = False):
    print("🔄 Starting Weekly Profile Updates")
    print("=" * 50)
    
    if target_students:
        students_to_update = target_students
        print(f"Updating specific students: {students_to_update}")
    elif force_update:
        students_to_update = get_students_with_recent_activity(days=30)
        print("Force update mode - processing all recently active students")
    else:
        students_to_update = get_students_needing_profile_update()
    
    if not students_to_update:
        print("No students found for profile updates.")
        return
    
    print(f"\nProcessing {len(students_to_update)} students...")
    
    results = []
    
    for i, student_id in enumerate(students_to_update, 1):
        print(f"\n[{i}/{len(students_to_update)}] Processing student: {student_id}")
        
        try:
            result = await analyze_and_update_profile(student_id, analysis_type="weekly")
            results.append(result)
            
            if result.get("save_status") == "success":
                evidence_count = result.get("evidence_count", 0)
                print(f"✅ Success - {evidence_count} evidence items processed")
            else:
                print(f"⚠️  Warning - {result.get('error', 'Unknown issue')}")
                
        except Exception as e:
            print(f"❌ Error processing {student_id}: {e}")
            results.append({
                "student_id": student_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("📊 WEEKLY UPDATE SUMMARY")
    print("=" * 50)
    
    successful = len([r for r in results if r.get("save_status") == "success"])
    failed = len([r for r in results if "error" in r])
    
    print(f"Total Students Processed: {len(results)}")
    print(f"Successful Updates: {successful}")
    print(f"Failed Updates: {failed}")
    
    if successful > 0:
        total_evidence = sum(r.get("evidence_count", 0) for r in results if r.get("save_status") == "success")
        print(f"Total Evidence Items Processed: {total_evidence}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"weekly_update_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Detailed results saved to: {results_file}")

def list_active_students(days: int = 7):
    students = get_students_with_recent_activity(days)
    
    if not students:
        print(f"No students with activity in the last {days} days.")
        return
    
    print(f"Students with activity in the last {days} days:")
    print("-" * 30)
    for student_id in students:
        print(f"  {student_id}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        print("Weekly Profile Updates Script")
        print("Usage:")
        print("  python weekly_profile_updates.py list [days]          # List active students")
        print("  python weekly_profile_updates.py run                  # Run updates for students needing them")
        print("  python weekly_profile_updates.py run --force          # Force update all active students")
        print("  python weekly_profile_updates.py run student_id       # Update specific student")
        print("  python weekly_profile_updates.py run id1,id2,id3      # Update specific students")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        list_active_students(days)
    
    elif command == "run":
        target_students = None
        force_update = False
        
        if len(sys.argv) > 2:
            if sys.argv[2] == "--force":
                force_update = True
            else:
                student_arg = sys.argv[2]
                if "," in student_arg:
                    target_students = [s.strip() for s in student_arg.split(",")]
                else:
                    target_students = [student_arg.strip()]
        
        asyncio.run(run_weekly_profile_updates(target_students, force_update))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
