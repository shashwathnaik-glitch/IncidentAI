import os
import math
import pytest
import psycopg2
from unittest.mock import MagicMock
from psycopg2 import OperationalError
from psycopg2.extensions import TransactionRollbackError

# Setup environment variables for test execution
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "26257")
os.environ.setdefault("DB_NAME", "defaultdb")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "")
os.environ.setdefault("DB_SSLMODE", "disable")

from backend.db.connection import get_connection, release_connection, execute_transaction, cockroach_transaction_retry
from backend.db.memory_store import (
    add_user, add_incident, add_solution_attempt, search_similar_incidents,
    get_solution_attempts, get_incident, normalize_vector, vector_to_string
)

def parse_vector_string(vec_str):
    """Parses a pgvector/CockroachDB vector string representation '[1.0,0.0,...]' to a list of floats."""
    if not vec_str:
        return []
    return [float(x.strip()) for x in vec_str.strip("[]").split(",") if x.strip()]

@pytest.fixture(scope="session")
def setup_database():
    """Session fixture to verify CockroachDB is running, apply migration schema, and fail clearly if unreachable."""
    try:
        conn = get_connection()
        release_connection(conn)
    except psycopg2.OperationalError as e:
        # Fulfills Modification 1: Do not auto-download binary, fail clearly with actionable message.
        pytest.fail(
            f"\n\n========================================================================\n"
            f"COCKROACHDB CONNECTION ERROR: {e}\n\n"
            f"Please ensure that the local CockroachDB instance is running in Docker.\n"
            f"You can start the database by executing:\n"
            f"    docker-compose up -d db\n"
            f"========================================================================\n"
        )
    # Run the SQL migration file to initialize tables, constraints, and index
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations",
        "001_init.sql"
    )
    with open(migration_file, "r") as f:
        migration_sql = f.read()
        
    conn = get_connection()
    try:
        old_autocommit = conn.autocommit
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute("SET CLUSTER SETTING feature.vector_index.enabled = true;")
            except Exception:
                pass
            cur.execute(migration_sql)
        conn.autocommit = old_autocommit
    finally:
        release_connection(conn)
    yield

@pytest.fixture()
def clean_tables(setup_database):
    """Truncates tables before each test run to ensure isolated test states. Depends on setup_database."""
    def _clean(cur):
        cur.execute("TRUNCATE TABLE solution_attempts, incidents, users CASCADE;")
    execute_transaction(_clean)

def test_user_creation(setup_database, clean_tables):
    """Verifies that user profiles are created correctly."""
    user = add_user("engineer@company.com", "hashed_pwd", "employee")
    assert user["id"] is not None
    assert user["email"] == "engineer@company.com"
    assert user["role"] == "employee"

def test_normalization_safeguard(setup_database, clean_tables):
    """Verifies that input embeddings are normalized to unit length before insertion."""
    # Create non-unit length vector (magnitude = 5.0)
    unnormalized_vector = [5.0] + [0.0] * 1023
    
    incident = add_incident(
        title="CPU Spike",
        description="CPU reached 100% on server-2",
        severity="high",
        category="infrastructure",
        logs="high cpu load",
        embedding=unnormalized_vector
    )
    
    # Retrieve the raw vector string directly from the database to check stored values
    def _get_raw_vector(cur):
        cur.execute("SELECT embedding FROM incidents WHERE id = %s;", (incident["id"],))
        return cur.fetchone()[0]
    
    stored_vector_str = execute_transaction(_get_raw_vector)
    stored_vector = parse_vector_string(stored_vector_str)
    
    # Verify vector dimension is preserved
    assert len(stored_vector) == 1024
    
    # Verify magnitude is now exactly 1.0 (unit-length normalized)
    magnitude = math.sqrt(sum(x * x for x in stored_vector))
    assert math.isclose(magnitude, 1.0, rel_tol=1e-5)
    
    # First element should be 1.0 (since unnormalized was [5, 0, ...])
    assert math.isclose(stored_vector[0], 1.0, rel_tol=1e-5)

def test_solution_attempts_no_overwrite(setup_database, clean_tables):
    """Verifies that historical solution attempts are preserved and never overwritten."""
    # 1. Create dependencies
    user = add_user("sre@company.com", "hashed_pwd", "employee")
    incident = add_incident(
        title="Disk Full",
        description="Out of disk space on mount /data",
        severity="critical",
        category="storage",
        logs="no space left on device",
        embedding=[1.0] + [0.0] * 1023
    )
    
    # 2. Add first attempt: Fix A -> FAILURE
    attempt1 = add_solution_attempt(
        incident_id=incident["id"],
        solution_text="Restart service",
        outcome="failure",
        failure_reason="service failed to start due to no disk space",
        performed_by=user["id"],
        execution_duration_ms=1200,
        confidence_at_execution=0.75,
        reward_delta=-10
    )
    
    # 3. Add second attempt: Fix B -> SUCCESS
    attempt2 = add_solution_attempt(
        incident_id=incident["id"],
        solution_text="Clear tmp files",
        outcome="success",
        performed_by=user["id"],
        execution_duration_ms=4500,
        confidence_at_execution=0.90,
        reward_delta=20
    )
    
    # 4. Add third attempt: Fix C -> REJECTED
    attempt3 = add_solution_attempt(
        incident_id=incident["id"],
        solution_text="Reboot host",
        outcome="rejected",
        failure_reason="Admin did not approve automatic reboot",
        performed_by=user["id"],
        execution_duration_ms=100,
        confidence_at_execution=0.50,
        reward_delta=0
    )
    
    # 5. Fetch and verify all records survive
    attempts = get_solution_attempts(incident["id"])
    assert len(attempts) == 3
    
    # Order should be DESC by created_at (attempt3, attempt2, attempt1)
    assert attempts[0]["solution_text"] == "Reboot host"
    assert attempts[0]["outcome"] == "rejected"
    
    assert attempts[1]["solution_text"] == "Clear tmp files"
    assert attempts[1]["outcome"] == "success"
    
    assert attempts[2]["solution_text"] == "Restart service"
    assert attempts[2]["outcome"] == "failure"
    assert attempts[2]["failure_reason"] == "service failed to start due to no disk space"

def test_similarity_search_and_metrics(setup_database, clean_tables):
    """Verifies similarity search returns correct ordering and accurate cosine similarity scores."""
    # Create two orthogonal incidents
    # Incident A: [1.0, 0.0, ...]
    vec_a = [1.0] + [0.0] * 1023
    incident_a = add_incident("Database Lockup", "Postgres lock conflict", "high", "database", "deadlock", vec_a)
    
    # Incident B: [0.0, 1.0, ...]
    vec_b = [0.0, 1.0] + [0.0] * 1022
    incident_b = add_incident("API Slowdown", "Gateway timeout", "medium", "network", "slow response", vec_b)
    
    # Add solution history to check they are fetched
    add_solution_attempt(incident_a["id"], "Kill blocker pid", "success")
    
    # Query with vector closer to A: [0.8, 0.6, ...] -> normalized magnitude is 1.0
    query_vec = [0.8, 0.6] + [0.0] * 1022
    
    results = search_similar_incidents(query_vec, limit=5)
    assert len(results) == 2
    
    # Incident A should rank higher (cosine similarity = 0.8) than B (cosine similarity = 0.6)
    assert results[0]["id"] == incident_a["id"]
    assert math.isclose(results[0]["similarity"], 0.8, rel_tol=1e-3)
    assert len(results[0]["solution_attempts"]) == 1
    assert results[0]["solution_attempts"][0]["solution_text"] == "Kill blocker pid"
    
    assert results[1]["id"] == incident_b["id"]
    assert math.isclose(results[1]["similarity"], 0.6, rel_tol=1e-3)

def test_explain_uses_vector_index(setup_database, clean_tables):
    """Verifies that vector similarity searches use the native vector index to avoid full sequential scans."""
    query_vec = vector_to_string([1.0] + [0.0] * 1023)
    
    def _run_explain(cur):
        cur.execute(
            f"""
            EXPLAIN
            SELECT id FROM incidents
            ORDER BY embedding <-> %s
            LIMIT 1;
            """,
            (query_vec,)
        )
        return "\n".join(row[0] for row in cur.fetchall())
        
    explain_output = execute_transaction(_run_explain).lower()
    
    # Assert that the query plan references vector index or index scan rather than full scan
    # CockroachDB vector index explain contains index name "idx_incidents_embedding" or "vector" reference.
    assert "idx_incidents_embedding" in explain_output or "vector" in explain_output

def test_transaction_retry_handler():
    """Tests the psycopg2 client-side decorator handles CockroachDB transaction serialization retry errors (40001)."""
    class MockOperationalError(psycopg2.OperationalError):
        def __init__(self, msg, pgcode):
            self.msg = msg
            self._pgcode = pgcode
        @property
        def pgcode(self):
            return self._pgcode

    calls = 0
    
    @cockroach_transaction_retry(max_retries=3, backoff_factor=0.01)
    def dummy_transaction():
        nonlocal calls
        calls += 1
        if calls == 1:
            # Raise MockOperationalError with SQLSTATE 40001 (serialization failure)
            raise MockOperationalError("Serialization conflict", "40001")
        return "success_val"
        
    res = dummy_transaction()
    assert res == "success_val"
    assert calls == 2
