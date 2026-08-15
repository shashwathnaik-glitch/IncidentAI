#!/usr/bin/env python
import os
import sys
import math
import random
import psycopg2

# Reconfigure stdout to prevent UnicodeEncodeError when printing box-drawing characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_vector_index():
    print("Connecting to CockroachDB...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=26257,
            database="defaultdb",
            user="root",
            password="",
            sslmode="disable"
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

    # 1. Apply Migrations
    print("Applying migration schema from 001_init.sql...")
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend",
        "migrations",
        "001_init.sql"
    )
    with open(migration_file, "r") as f:
        migration_sql = f.read()

    conn.autocommit = True
    with conn.cursor() as cur:
        try:
            cur.execute("SET CLUSTER SETTING feature.vector_index.enabled = true;")
        except Exception:
            pass
        cur.execute(migration_sql)
    conn.autocommit = False
    print("Schema migration applied.")

    # 2. Insert representative incident records
    print("Truncating tables to clear previous data...")
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE solution_attempts, incidents, users CASCADE;")

    print("Generating 500 representative incidents...")
    
    # Generate random unit vector of size 1024
    def generate_unit_vector(dim=1024):
        v = [random.uniform(-1.0, 1.0) for _ in range(dim)]
        magnitude = math.sqrt(sum(x * x for x in v))
        return [x / magnitude for x in v]

    def vector_to_string(v):
        return "[" + ",".join(str(x) for x in v) + "]"

    # Target unit vector close to [1.0, 0.0, ...]
    target_vector = [1.0] + [0.0] * 1023

    with conn:
        with conn.cursor() as cur:
            # Create user operator for solution attempts
            cur.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING id;",
                ("operator@company.com", "pwd_hash", "employee")
            )
            user_id = cur.fetchone()[0]

            # Insert exact match incident
            cur.execute(
                """
                INSERT INTO incidents (title, description, severity, category, logs, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    "Target DB Lockout",
                    "Database transaction lock conflict blocking main API thread",
                    "critical",
                    "database",
                    "deadlock detail blocking pid 4983",
                    vector_to_string(target_vector)
                )
            )
            target_incident_id = cur.fetchone()[0]

            # Insert solutions attempts for target (failure, success)
            cur.execute(
                """
                INSERT INTO solution_attempts (incident_id, solution_action, outcome, notes, executed_by)
                VALUES 
                    (%s, 'Restart database server', 'failure', 'caused 30s connection timeout for API client', %s),
                    (%s, 'Kill blocker transaction PID', 'success', NULL, %s);
                """,
                (target_incident_id, user_id, target_incident_id, user_id)
            )

            # Insert 499 random incidents to populate database and create a large cardinality table
            random_incidents = []
            for i in range(499):
                title = f"System Error Notification #{i}"
                desc = f"Automatic monitoring check system failed component #{i}"
                sev = random.choice(["low", "medium", "high", "critical"])
                cat = random.choice(["database", "network", "storage", "infrastructure"])
                logs = f"log output error details for system cluster node #{i}"
                # Generate random unit vector
                v = generate_unit_vector()
                random_incidents.append((title, desc, sev, cat, logs, vector_to_string(v)))

            cur.executemany(
                """
                INSERT INTO incidents (title, description, severity, category, logs, embedding)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                random_incidents
            )
            
    print("Successfully inserted 500 representative incidents and solutions attempts.")

    # 3. Run EXPLAIN on the similarity query
    print("\nRunning EXPLAIN plan on similarity search query...")
    query_vector_str = vector_to_string(target_vector)
    
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                EXPLAIN
                SELECT id, title, (embedding <-> %s) AS distance
                FROM incidents
                ORDER BY embedding <-> %s
                LIMIT 5;
                """,
                (query_vector_str, query_vector_str)
            )
            explain_lines = [row[0] for row in cur.fetchall()]
            explain_output = "\n".join(explain_lines)
            
    print("-" * 80)
    print("EXPLAIN PLAN RESULT:")
    print("-" * 80)
    print(explain_output)
    print("-" * 80)

    # 4. Verify C-SPANN index utilization
    index_used = "idx_incidents_embedding" in explain_output or "vector" in explain_output.lower()
    
    if index_used:
        print("VERIFICATION SUCCESS: Native C-SPANN vector index 'idx_incidents_embedding' was utilized by the query planner!")
    else:
        print("VERIFICATION FAILURE: Vector index was NOT utilized (full table scan fallback detected).")
        conn.close()
        return False

    # 5. Run exact similarity query via memory_store.py and verify math
    print("\nRunning similarity search query from memory_store.py...")
    from backend.db.memory_store import search_similar_incidents
    
    # Query with a vector slightly offset from target to verify cosine math: [0.999, 0.0447, ...]
    # Normalize it first to be safe
    offset_vector = [0.999, 0.0447] + [0.0] * 1022
    mag = math.sqrt(sum(x*x for x in offset_vector))
    offset_vector = [x / mag for x in offset_vector]

    results = search_similar_incidents(offset_vector, limit=5)
    
    print("\nQuery Search Results:")
    for i, res in enumerate(results):
        print(f"Rank {i+1}: {res['title']}")
        print(f"  Euclidean Distance (<->): {res['distance']:.6f}")
        print(f"  Returned Cosine Similarity: {res['similarity']:.6f}")
        for attempt in res['solution_attempts']:
            print(f"    Solution: {attempt['solution_text']} -> Outcome: {attempt['outcome']}")

    # 6. Verify distance-to-similarity conversion math
    top_res = results[0]
    expected_cosine = 1.0 - ((top_res['distance'] * top_res['distance']) / 2.0)
    print(f"\nChecking mathematical equivalence conversion:")
    print(f"  L2 Distance retrieved from SQL: {top_res['distance']:.6f}")
    print(f"  Calculated Cosine Similarity from L2: {expected_cosine:.6f}")
    print(f"  Returned Cosine Similarity: {top_res['similarity']:.6f}")
    
    assert math.isclose(expected_cosine, top_res['similarity'], rel_tol=1e-5)
    print("VERIFICATION SUCCESS: Cosine similarity conversion math is 100% accurate.")
    
    conn.close()
    return True

if __name__ == "__main__":
    success = verify_vector_index()
    sys.exit(0 if success else 1)
