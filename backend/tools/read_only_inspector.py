"""
Read-Only Database Inspector for IncidentMind.

This utility inspects the schemas, column metadata, and index configurations 
of the running CockroachDB instance to verify repository alignment. 
No changes, modifications, or mock data operations are executed.
"""

import os
import sys
import psycopg2

# Adjust path to enable importing backend configurations
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def mask_val(var_name, val):
    if not val:
        return "<Not Set>"
    if "password" in var_name.lower() or "url" in var_name.lower():
        return "*** [Masked for Security]"
    return val

def inspect_state():
    print("=== ENVIRONMENT CONFIGURATION ===")
    for var in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_SSLMODE", "DATABASE_URL", "USE_REAL_DB", "TESTING"]:
        val = os.environ.get(var)
        print(f" - {var}: {mask_val(var, val)}")

    print("\n=== SYSTEM PATHS AND SETTINGS ===")
    try:
        from backend.core.config import settings
        print(f" - settings.DATABASE_NAME: {settings.DATABASE_NAME}")
        # Note: settings.get_database_connection_url() is masked for security.
        print(f" - settings.DATABASE_HOST: {settings.DATABASE_HOST}")
        print(f" - settings.DATABASE_PORT: {settings.DATABASE_PORT}")
        print(f" - settings.DATABASE_USER: {settings.DATABASE_USER}")
    except Exception as e:
        print(f" - Error loading settings: {e}")

    target_db = "incidentmind"
    try:
        # Connect directly to target_db to ensure pg_indexes and information_schema resolve correctly
        conn = psycopg2.connect(
            host="localhost",
            port=26257,
            database=target_db,
            user="root",
            password="",
            sslmode="disable"
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            print(f"\n=== DATABASE SCHEMA: {target_db} ===")
            schema_columns = {}
            for table in ["users", "incidents", "solution_attempts"]:
                cur.execute(
                    f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = '{table}'
                    ORDER BY ordinal_position;
                    """
                )
                rows = cur.fetchall()
                schema_columns[table] = [row[0] for row in rows]
                print(f" Table '{table}' columns:")
                if not rows:
                    print("   (Table does not exist or has no columns)")
                for row in rows:
                    print(f"   - {row[0]}: type={row[1]}, nullable={row[2]}")
            
            print(f"\n=== DATABASE INDEXES: {target_db} ===")
            cur.execute(
                f"""
                SELECT tablename, indexname, indexdef 
                FROM pg_indexes 
                WHERE schemaname = 'public' AND tablename IN ('users', 'incidents', 'solution_attempts');
                """
            )
            indexes = cur.fetchall()
            for idx in indexes:
                print(f" - Table: {idx[0]}, Index Name: {idx[1]}")
                print(f"   Definition: {idx[2]}")

            print(f"\n=== REPOSITORY ALIGNMENT COMPARISON ===")
            expected = {
                "users": ["id", "email", "password_hash", "name", "role", "department", "created_at"],
                "incidents": ["id", "title", "description", "category", "severity", "status", "reported_by", "created_at", "updated_at"],
                "solution_attempts": ["id", "incident_id", "solution_action", "outcome", "notes", "executed_by", "created_at"]
            }
            
            for table, cols in expected.items():
                actual = schema_columns.get(table, [])
                missing = [c for c in cols if c not in actual]
                print(f" Table '{table}':")
                print(f"   Expected: {cols}")
                print(f"   Actual: {actual}")
                if missing:
                    print(f"   [MISMATCH] Missing expected columns: {missing}")
                else:
                    print(f"   [ALIGNED] All expected columns are present.")
                    
        conn.close()
    except Exception as e:
        print(f"\nError connecting to inspect database: {e}")

if __name__ == "__main__":
    inspect_state()
