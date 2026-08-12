import sqlite3
import json
import sys
from pathlib import Path

# DB Path is in backend relative to the root directory
# We can find the database relative to this script
CURRENT_DIR = Path(__file__).resolve().parent
DB_PATH = CURRENT_DIR.parent.parent / "backend" / "finvoice_memory.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def list_escalations():
    try:
        if not DB_PATH.exists():
            return []
        
        with get_connection() as conn:
            # Check if table exists
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='escalations'")
            if not cursor.fetchone():
                return []
            
            cursor = conn.execute("SELECT * FROM escalations ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error listing: {e}", file=sys.stderr)
        return []

def update_status(ref_id, status):
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE escalations SET status = ? WHERE reference_id = ?",
                (status, ref_id)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Error updating: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "list":
            res = list_escalations()
            print(json.dumps(res))
        elif action == "update" and len(sys.argv) > 3:
            ref_id = sys.argv[2]
            status = sys.argv[3]
            success = update_status(ref_id, status)
            print(json.dumps({"success": success}))
        else:
            print(json.dumps({"error": "Unknown action or missing arguments"}))
    else:
        print(json.dumps({"error": "No arguments provided"}))
