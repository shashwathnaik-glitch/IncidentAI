import math
import logging
from backend.db.connection import execute_transaction

logger = logging.getLogger("memory_store")

def normalize_vector(v):
    """Normalizes a vector (list of floats) to unit length (L2 norm = 1.0) as a safeguard."""
    if not v:
        return None
    try:
        # Calculate L2 norm (magnitude)
        magnitude = math.sqrt(sum(float(x) * float(x) for x in v))
        if magnitude == 0:
            return v
        return [float(x) / magnitude for x in v]
    except Exception as e:
        logger.error(f"Error normalizing vector: {e}")
        raise ValueError(f"Invalid vector format: {e}")

def vector_to_string(v):
    """Converts a list of floats to a pgvector-compatible string representation [val1, val2, ...]."""
    if not v:
        return None
    return "[" + ",".join(str(x) for x in v) + "]"

def add_user(email, password_hash, role):
    """Creates a new user operator."""
    def _tx(cur):
        cur.execute(
            """
            INSERT INTO users (email, password_hash, role)
            VALUES (%s, %s, %s)
            RETURNING id, email, role, created_at;
            """,
            (email, password_hash, role)
        )
        row = cur.fetchone()
        return {"id": row[0], "email": row[1], "role": row[2], "created_at": row[3]}
    return execute_transaction(_tx)

def add_incident(title, description, severity, category, logs, embedding):
    """Creates a new incident, normalizing the vector embedding before saving."""
    normalized_emb = vector_to_string(normalize_vector(embedding))
    
    def _tx(cur):
        cur.execute(
            """
            INSERT INTO incidents (title, description, severity, category, logs, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, title, description, severity, category, status, logs, created_at;
            """,
            (title, description, severity, category, logs, normalized_emb)
        )
        row = cur.fetchone()
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "severity": row[3],
            "category": row[4],
            "status": row[5],
            "logs": row[6],
            "created_at": row[7]
        }
    return execute_transaction(_tx)

def add_solution_attempt(
    incident_id,
    solution_text,
    outcome,
    failure_reason=None,
    performed_by=None,
    execution_duration_ms=None,
    confidence_at_execution=None,
    reward_delta=None
):
    """
    Appends a new solution attempt.
    CRITICAL RULE: Historical solution attempts are never overwritten or updated.
    Every single attempt generates a new record.
    """
    def _tx(cur):
        cur.execute(
            """
            INSERT INTO solution_attempts (
                incident_id, solution_action, outcome, notes, 
                executed_by, execution_duration_ms, confidence_at_execution, reward_delta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, incident_id, solution_action, outcome, notes, created_at;
            """,
            (
                incident_id,
                solution_text,
                outcome,
                failure_reason,
                performed_by,
                execution_duration_ms,
                confidence_at_execution,
                reward_delta
            )
        )
        row = cur.fetchone()
        return {
            "id": row[0],
            "incident_id": row[1],
            "solution_text": row[2],
            "outcome": row[3],
            "failure_reason": row[4],
            "created_at": row[5]
        }
    return execute_transaction(_tx)

def search_similar_incidents(embedding, limit=5):
    """
    Searches for semantically similar incidents using L2/Euclidean distance operator (<->).
    Leverages the CockroachDB vector index.
    Because vectors are normalized, Cosine Similarity is calculated as: 1 - (L2_Distance^2 / 2).
    Also collects the history of solution attempts for each matched incident.
    """
    normalized_emb = vector_to_string(normalize_vector(embedding))

    def _tx(cur):
        # 1. Fetch similar incidents using vector index
        cur.execute(
            """
            SELECT id, title, description, severity, category, status, logs, (embedding <-> %s) AS distance, created_at
            FROM incidents
            ORDER BY embedding <-> %s
            LIMIT %s;
            """,
            (normalized_emb, normalized_emb, limit)
        )
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            inc_id = row[0]
            distance = row[7]
            # Convert Euclidean distance to exact Cosine Similarity for the AI/Backend roles
            cosine_similarity = 1.0 - ((distance * distance) / 2.0) if distance is not None else 0.0
            
            # 2. Collect solution attempts for this incident
            cur.execute(
                """
                SELECT id, solution_action, outcome, notes, executed_by, 
                       execution_duration_ms, confidence_at_execution, reward_delta, created_at
                FROM solution_attempts
                WHERE incident_id = %s
                ORDER BY created_at DESC;
                """,
                (inc_id,)
            )
            attempt_rows = cur.fetchall()
            attempts = []
            for a in attempt_rows:
                attempts.append({
                    "id": a[0],
                    "solution_text": a[1],
                    "outcome": a[2],
                    "failure_reason": a[3],
                    "performed_by": a[4],
                    "execution_duration_ms": a[5],
                    "confidence_at_execution": a[6],
                    "reward_delta": a[7],
                    "created_at": a[8]
                })

            results.append({
                "id": inc_id,
                "title": row[1],
                "description": row[2],
                "severity": row[3],
                "category": row[4],
                "status": row[5],
                "logs": row[6],
                "distance": distance,
                "similarity": cosine_similarity,
                "created_at": row[8],
                "solution_attempts": attempts
            })
        return results
    return execute_transaction(_tx)

def get_solution_attempts(incident_id):
    """Retrieves all attempts for a specific incident."""
    def _tx(cur):
        cur.execute(
            """
            SELECT id, solution_action, outcome, notes, executed_by, 
                   execution_duration_ms, confidence_at_execution, reward_delta, created_at
            FROM solution_attempts
            WHERE incident_id = %s
            ORDER BY created_at DESC;
            """,
            (incident_id,)
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "solution_text": r[1],
                "outcome": r[2],
                "failure_reason": r[3],
                "performed_by": r[4],
                "execution_duration_ms": r[5],
                "confidence_at_execution": r[6],
                "reward_delta": r[7],
                "created_at": r[8]
            }
            for r in rows
        ]
    return execute_transaction(_tx)

def get_incident(incident_id):
    """Retrieves incident metadata by ID (excludes embedding vector)."""
    def _tx(cur):
        cur.execute(
            """
            SELECT id, title, description, severity, category, status, logs, created_at
            FROM incidents
            WHERE id = %s;
            """,
            (incident_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "severity": row[3],
            "category": row[4],
            "status": row[5],
            "logs": row[6],
            "created_at": row[7]
        }
    return execute_transaction(_tx)

def get_all_incidents(status_filter="ALL", search_query=None, limit=20, offset=0):
    """Retrieves all incidents with optional status filtering and search query."""
    def _tx(cur):
        query = "SELECT id, title, description, severity, category, status, logs, created_at FROM incidents WHERE 1=1"
        params = []
        if status_filter and status_filter.upper() != "ALL":
            query += " AND UPPER(status) = %s"
            params.append(status_filter.upper())
        if search_query:
            query += " AND (title ILIKE %s OR category ILIKE %s OR description ILIKE %s)"
            search_param = f"%{search_query}%"
            params.extend([search_param, search_param, search_param])
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s;"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "title": r[1],
                "description": r[2],
                "severity": r[3],
                "category": r[4],
                "status": r[5],
                "logs": r[6],
                "created_at": r[7]
            }
            for r in rows
        ]
    return execute_transaction(_tx)
