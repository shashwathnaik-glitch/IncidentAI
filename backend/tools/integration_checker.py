"""
End-to-End Integration Diagnostic Checker for Incident AI.

This script executes safety-constrained read-only schema checks, self-cleaning 
smoke-tests for the persistence layers, API routes discovery, and frontend contract 
mismatch parsing to ensure CockroachDB is correctly configured.
"""

import os
import sys
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
import psycopg2

# Adjust path to enable importing backend configurations
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def format_status(status_val):
    if status_val:
        return "[PASS]"
    return "[FAIL]"

def run_integration_checker():
    # Track passes, warnings, and failures
    results = {
        "config": False,
        "connectivity": False,
        "schema": False,
        "repo_health": False,
        "auth_repo": False,
        "incident_persistence": False,
        "solution_persistence": False,
        "api_health": "WARN",
        "frontend_contract": "WARN"
    }
    
    passes = 0
    warningss = 0
    failures = 0
    
    reasons = []
    
    print("========================================")
    print("    INCIDENT AI INTEGRATION CHECK")
    print("========================================")
    
    # ----------------------------------------------------
    # 1. Configuration Check
    # ----------------------------------------------------
    print("\n[1/9] Checking Configuration...")
    try:
        from backend.core.config import settings, USE_REAL_DB
        
        cfg_errors = []
        if settings.TESTING:
            cfg_errors.append("settings.TESTING is True (Expected: False for real DB)")
        if not USE_REAL_DB:
            cfg_errors.append("USE_REAL_DB is False (Expected: True for real DB)")
        if settings.DATABASE_NAME != "incidentmind":
            cfg_errors.append(f"settings.DATABASE_NAME is '{settings.DATABASE_NAME}' (Expected: 'incidentmind')")
        if settings.DATABASE_HOST != "localhost":
            cfg_errors.append(f"settings.DATABASE_HOST is '{settings.DATABASE_HOST}' (Expected: 'localhost')")
        if settings.DATABASE_PORT != 26257:
            cfg_errors.append(f"settings.DATABASE_PORT is {settings.DATABASE_PORT} (Expected: 26257)")
        if settings.DATABASE_USER != "root":
            cfg_errors.append(f"settings.DATABASE_USER is '{settings.DATABASE_USER}' (Expected: 'root')")
            
        if not cfg_errors:
            results["config"] = True
            passes += 1
            print(" [OK] Configuration matches required real database runtime settings.")
        else:
            reasons.extend(cfg_errors)
            failures += len(cfg_errors)
            print(" [ERROR] Configuration mismatch detected:")
            for err in cfg_errors:
                print(f"   - {err}")
    except Exception as e:
        failures += 1
        reasons.append(f"Failed to import or read config: {e}")
        print(f" [ERROR] Configuration read failed: {e}")

    # ----------------------------------------------------
    # 2. CockroachDB Connectivity Check
    # ----------------------------------------------------
    print("\n[2/9] Checking Database Connectivity...")
    conn = None
    try:
        from backend.core.config import settings
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password="",
            sslmode="disable"
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            res = cur.fetchone()
            if res and res[0] == 1:
                results["connectivity"] = True
                passes += 1
                print(f" [OK] Successfully connected to '{settings.DATABASE_NAME}' and ran SELECT 1.")
            else:
                failures += 1
                reasons.append("SELECT 1 returned invalid value")
                print(" [ERROR] SELECT 1 returned unexpected results.")
    except Exception as e:
        failures += 1
        reasons.append(f"Database connection failed: {e}")
        print(f" [ERROR] Connectivity failed: {e}")

    # ----------------------------------------------------
    # 3. Schema Alignment Check
    # ----------------------------------------------------
    print("\n[3/9] Checking Database Schema Alignment...")
    if conn:
        try:
            schema_ok = True
            expected_schemas = {
                "users": ["id", "email", "password_hash", "name", "role", "department", "created_at"],
                "incidents": ["id", "title", "description", "category", "severity", "status", "reported_by", "created_at", "updated_at"],
                "solution_attempts": ["id", "incident_id", "solution_action", "outcome", "notes", "executed_by", "created_at"]
            }
            
            with conn.cursor() as cur:
                for table, columns in expected_schemas.items():
                    cur.execute(
                        """
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s;
                        """,
                        (table,)
                    )
                    rows = cur.fetchall()
                    actual_columns = {row[0]: row[1] for row in rows}
                    
                    missing = [col for col in columns if col not in actual_columns]
                    if missing:
                        schema_ok = False
                        failures += 1
                        reasons.append(f"Table '{table}' is missing expected columns: {missing}")
                        print(f" [ERROR] Table '{table}' is missing columns: {missing}")
                    else:
                        print(f" [OK] Table '{table}' columns are fully aligned.")
                        
                    # Extra check for vector column type
                    if table == "incidents":
                        emb_type = actual_columns.get("embedding")
                        if not emb_type or "vector" not in emb_type.lower():
                            schema_ok = False
                            failures += 1
                            reasons.append(f"incidents.embedding column is type '{emb_type}' instead of vector")
                            print(f" [ERROR] incidents.embedding is '{emb_type}' instead of vector.")
                        else:
                            print(" [OK] incidents.embedding type is confirmed as vector.")
                            
                # Verify vector index
                cur.execute(
                    """
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'public' AND tablename = 'incidents' AND indexname = 'idx_incidents_embedding';
                    """
                )
                idx = cur.fetchone()
                if not idx:
                    schema_ok = False
                    failures += 1
                    reasons.append("Vector index 'idx_incidents_embedding' is missing")
                    print(" [ERROR] Vector index 'idx_incidents_embedding' was not found.")
                else:
                    print(" [OK] Vector index 'idx_incidents_embedding' is present.")
                    
            if schema_ok:
                results["schema"] = True
                passes += 1
        except Exception as e:
            failures += 1
            reasons.append(f"Schema check error: {e}")
            print(f" [ERROR] Schema verification failed: {e}")
    else:
        failures += 1
        reasons.append("Skipped schema verification because database connection failed")
        print(" [SKIP] Database connection unavailable for schema check.")

    # ----------------------------------------------------
    # 4. Repository Smoke Test
    # ----------------------------------------------------
    print("\n[4/9] Verifying CockroachDBRepository Health Check...")
    try:
        from backend.database.cockroach_repository import CockroachDBRepository
        repo = CockroachDBRepository()
        if repo.check_connection_health():
            results["repo_health"] = True
            passes += 1
            print(" [OK] CockroachDBRepository.check_connection_health() returned True.")
        else:
            failures += 1
            reasons.append("CockroachDBRepository.check_connection_health() returned False")
            print(" [ERROR] CockroachDBRepository.check_connection_health() failed.")
    except Exception as e:
        failures += 1
        reasons.append(f"Failed to check repository health: {e}")
        print(f" [ERROR] Repository health check failed: {e}")

    # ----------------------------------------------------
    # 5. Authentication Smoke Test
    # ----------------------------------------------------
    print("\n[5/9] Running Authentication Smoke Test...")
    unique_id = str(uuid.uuid4())
    test_email = f"integration_checker_user_{unique_id[:8]}@company.com"
    test_user_id = None
    
    if conn:
        try:
            from backend.core.security import get_password_hash, verify_password
            from backend.database.cockroach_repository import CockroachDBRepository
            
            pwd_hash = get_password_hash("Password123!")
            repo = CockroachDBRepository()
            
            # Insert temporary user via direct SQL
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, role, name, department)
                    VALUES (%s, %s, 'employee', 'Diagnostic Checker User', 'QA')
                    RETURNING id;
                    """,
                    (test_email, pwd_hash)
                )
                test_user_id = cur.fetchone()[0]
                
            # Verify retrieval via repository method
            user_record = repo.get_user_by_email(test_email)
            if user_record and str(user_record.id) == str(test_user_id):
                pwd_ok = verify_password("Password123!", user_record.password_hash)
                if pwd_ok:
                    results["auth_repo"] = True
                    passes += 1
                    print(" [OK] Successfully persisted, retrieved, and verified user credentials.")
                else:
                    failures += 1
                    reasons.append("Password verification failed on retrieved user record")
                    print(" [ERROR] Password verification failed.")
            else:
                failures += 1
                reasons.append("Could not retrieve temporary user record using get_user_by_email()")
                print(" [ERROR] Temporary user record retrieval failed.")
        except Exception as e:
            failures += 1
            reasons.append(f"Authentication smoke test failed: {e}")
            print(f" [ERROR] Authentication test error: {e}")
        finally:
            if test_user_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM users WHERE id = %s;", (str(test_user_id),))
                    print(" [OK] Cleaned up temporary test user record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up test user: {clean_err}")
    else:
        failures += 1
        reasons.append("Skipped authentication test because database connection failed")
        print(" [SKIP] Connection unavailable for Auth smoke test.")

    # ----------------------------------------------------
    # 6. Incident Persitence Smoke Test
    # ----------------------------------------------------
    print("\n[6/9] Running Incident Persistence Smoke Test...")
    test_incident_id = None
    temp_reported_user_id = None
    if conn:
        try:
            from backend.database.cockroach_repository import CockroachDBRepository
            repo = CockroachDBRepository()
            
            # Setup temporary user for reported_by reference
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, role, name, department)
                    VALUES (%s, 'dummy_hash', 'employee', 'Incident Reporter', 'QA')
                    RETURNING id;
                    """,
                    (f"reporter_{unique_id[:8]}@company.com",)
                )
                temp_reported_user_id = cur.fetchone()[0]
            
            incident_payload = {
                "title": f"Checker Temp Incident {unique_id[:8]}",
                "description": "Uniquely identifiable diagnostic test incident of length greater than ten.",
                "category": "Database Check",
                "severity": "P3",
                "status": "open",
                "reported_by": temp_reported_user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            created_inc = repo.create_incident(incident_payload)
            test_incident_id = created_inc["id"]
            
            retrieved_inc = repo.get_incident_by_id(test_incident_id)
            if retrieved_inc and retrieved_inc["title"] == incident_payload["title"]:
                results["incident_persistence"] = True
                passes += 1
                print(" [OK] Incident successfully created, saved, and retrieved from database.")
            else:
                failures += 1
                reasons.append("Failed to retrieve or verify created incident values")
                print(" [ERROR] Incident retrieval comparison mismatch.")
        except Exception as e:
            failures += 1
            reasons.append(f"Incident persistence test failed: {e}")
            print(f" [ERROR] Incident persistence error: {e}")
        finally:
            if test_incident_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM incidents WHERE id = %s;", (str(test_incident_id),))
                    print(" [OK] Cleaned up temporary test incident record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up test incident: {clean_err}")
            if temp_reported_user_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM users WHERE id = %s;", (str(temp_reported_user_id),))
                    print(" [OK] Cleaned up temporary reporter user record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up reporter user: {clean_err}")
    else:
        failures += 1
        reasons.append("Skipped incident persistence test because database connection failed")
        print(" [SKIP] Connection unavailable for Incident smoke test.")

    # ----------------------------------------------------
    # 7. Solution Attempt persistence smoke test
    # ----------------------------------------------------
    print("\n[7/9] Running Solution Attempt Persistence Smoke Test...")
    temp_attempt_id = None
    temp_incident_id = None
    temp_user_id = None
    if conn:
        try:
            from backend.database.cockroach_repository import CockroachDBRepository
            repo = CockroachDBRepository()
            
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, role, name, department)
                    VALUES (%s, 'dummy_hash', 'employee', 'Sol Performer', 'QA')
                    RETURNING id;
                    """,
                    (f"performer_{unique_id[:8]}@company.com",)
                )
                temp_user_id = cur.fetchone()[0]
                
                cur.execute(
                    """
                    INSERT INTO incidents (title, description, category, severity, status, reported_by)
                    VALUES ('Sol Temp Incident', 'Temporary description longer than ten characters', 'DB', 'medium', 'active', %s)
                    RETURNING id;
                    """,
                    (str(temp_user_id),)
                )
                temp_incident_id = cur.fetchone()[0]
                
            attempt_payload = {
                "incident_id": temp_incident_id,
                "solution_action": "Check diagnostic outcome",
                "outcome": "success",
                "notes": "Diagnostics ran cleanly",
                "executed_by": temp_user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            created_attempt = repo.create_solution_attempt(attempt_payload)
            temp_attempt_id = created_attempt["id"]
            
            attempts = repo.get_solution_attempts_by_incident(temp_incident_id)
            if attempts and str(attempts[0]["id"]) == str(temp_attempt_id):
                results["solution_persistence"] = True
                passes += 1
                print(" [OK] Solution attempt successfully recorded and retrieved from database.")
            else:
                failures += 1
                reasons.append("Could not retrieve recorded solution attempt or ID mismatch")
                print(" [ERROR] Solution attempt verification failed.")
        except Exception as e:
            failures += 1
            reasons.append(f"Solution attempt persistence test failed: {e}")
            print(f" [ERROR] Solution attempt test error: {e}")
        finally:
            if temp_attempt_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM solution_attempts WHERE id = %s;", (str(temp_attempt_id),))
                    print(" [OK] Cleaned up temporary test solution attempt record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up solution attempt: {clean_err}")
            if temp_incident_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM incidents WHERE id = %s;", (str(temp_incident_id),))
                    print(" [OK] Cleaned up temporary test incident record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up test incident: {clean_err}")
            if temp_user_id:
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM users WHERE id = %s;", (str(temp_user_id),))
                    print(" [OK] Cleaned up temporary performer user record.")
                except Exception as clean_err:
                    print(f" [WARNING] Failed to clean up performer user: {clean_err}")
    else:
        failures += 1
        reasons.append("Skipped solution attempt persistence test because database connection failed")
        print(" [SKIP] Connection unavailable for Solution Attempt smoke test.")

    # ----------------------------------------------------
    # 8. API Health and Route Discovery
    # ----------------------------------------------------
    print("\n[8/9] Testing API Health / Endpoints...")
    discovered_health_paths = []
    try:
        from backend.main import app
        for route in app.routes:
            # Check for routes matching health checks
            if "/health" in route.path:
                discovered_health_paths.append(route.path)
        print(f" Discovered health route paths: {discovered_health_paths}")
    except Exception as e:
        print(f" Could not analyze backend routing tables: {e}")
        
    url_to_test = "http://127.0.0.1:8000/health"
    try:
        response = urllib.request.urlopen(url_to_test, timeout=2.0)
        code = response.getcode()
        if code == 200:
            results["api_health"] = "PASS"
            passes += 1
            print(f" [OK] GET request to '{url_to_test}' returned status {code}.")
        else:
            warningss += 1
            print(f" [WARNING] GET request to '{url_to_test}' returned unexpected status {code}.")
    except urllib.error.URLError as url_err:
        warningss += 1
        print(f" [WARNING] API health endpoint at '{url_to_test}' could not be reached (Is Uvicorn running?). Details: {url_err}")
    except Exception as e:
        warningss += 1
        print(f" [WARNING] API check failed: {e}")

    # ----------------------------------------------------
    # 9. Frontend/Backend Contract Mismatch Checks
    # ----------------------------------------------------
    print("\n[9/9] Inspecting Frontend/Backend Schema Contract...")
    js_path = r"c:\Users\Shashwath S Naik\Documents\CocroachDB X AWS Hackthon\frontend\src\services\incidentService.js"
    contract_ok = True
    
    if os.path.exists(js_path):
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                js_content = f.read()
                
            # Backend expects: P1, P2, P3, P4
            # Frontend has: CRITICAL, HIGH, MEDIUM, LOW
            # Look for severityMap converter in frontend js
            if "severityMap" in js_content:
                print(" [OK] Found 'severityMap' in incidentService.js translating severity values.")
                if "'CRITICAL': 'P1'" in js_content or '"CRITICAL": "P1"' in js_content:
                    print("   - CRITICAL translates to P1 (Expected)")
                else:
                    contract_ok = False
                    warningss += 1
                    print("   - [WARNING] CRITICAL severity translation mismatch or not found.")
                if "'HIGH': 'P2'" in js_content or '"HIGH": "P2"' in js_content:
                    print("   - HIGH translates to P2 (Expected)")
                else:
                    contract_ok = False
                    warningss += 1
                    print("   - [WARNING] HIGH severity translation mismatch or not found.")
            else:
                contract_ok = False
                warningss += 1
                print(" [WARNING] 'severityMap' converter not detected. Frontend severity values may mismatch backend severity levels (P1-P4).")
                
            # Check Status Case Mismatch
            # Backend expects lowercase: "open", "investigating", "resolved", "closed"
            # Look at INITIAL_INCIDENTS in frontend service
            if "status: 'OPEN'" in js_content or 'status: "OPEN"' in js_content:
                contract_ok = False
                warningss += 1
                print(" [WARNING] Frontend initial incident uses uppercase status ('OPEN'). Backend expects lowercase ('open').")
            if "status: 'INVESTIGATING'" in js_content or 'status: "INVESTIGATING"' in js_content:
                contract_ok = False
                warningss += 1
                print(" [WARNING] Frontend initial incident uses uppercase status ('INVESTIGATING'). Backend expects lowercase ('investigating').")
                
            if contract_ok:
                results["frontend_contract"] = "PASS"
                passes += 1
                print(" [OK] No obvious contract mismatches discovered.")
        except Exception as e:
            warningss += 1
            print(f" [WARNING] Error reading frontend file: {e}")
    else:
        warningss += 1
        print(f" [WARNING] Frontend service file not found at: {js_path}")

    # ----------------------------------------------------
    # 10. Final Report
    # ----------------------------------------------------
    print("\n" + "="*40)
    print("    INCIDENT AI INTEGRATION REPORT")
    print("="*40)
    print(f"{format_status(results['config'])} Configuration")
    print(f"{format_status(results['connectivity'])} CockroachDB connection")
    print(f"{format_status(results['schema'])} Schema alignment")
    print(f"{format_status(results['repo_health'])} Real repository health")
    print(f"{format_status(results['auth_repo'])} Authentication repository")
    print(f"{format_status(results['incident_persistence'])} Incident persistence")
    print(f"{format_status(results['solution_persistence'])} Solution attempt persistence")
    
    api_status = "[PASS]" if results["api_health"] == "PASS" else "[WARN]"
    print(f"{api_status} API health")
    
    contract_status = "[PASS]" if results["frontend_contract"] == "PASS" else "[WARN]"
    print(f"{contract_status} Frontend/backend contract")
    print("="*40)
    
    print("\n========================================")
    print("SUMMARY")
    print("========================================")
    print(f" - PASS: {passes}")
    print(f" - WARN: {warningss}")
    print(f" - FAIL: {failures}")
    
    if failures > 0 or warningss > 0:
        print("\n=== DIAGNOSTICS & RECOMMENDATIONS ===")
        if failures > 0:
            print(" [FAILURES]")
            for r in reasons:
                print(f"  - Reason: {r}")
            print("  Recommended Action: Resolve backend config files and align column mapping SQL statements.")
        if warningss > 0:
            print(" [WARNINGS]")
            print("  - Reason: Frontend incident status values ('OPEN', 'INVESTIGATING') are uppercase. Backend severity/status enums expect lowercase values ('open', 'investigating').")
            print("  - File: frontend/src/services/incidentService.js")
            print("  Recommended Action: Add converters in frontend request payload wrappers or database mappings to convert status strings to lowercase before sending to API routes.")
    else:
        print("\nAll integration check checkpoints completed successfully!")
    print("========================================")

if __name__ == "__main__":
    run_integration_checker()
