import os
import time
import random
import logging
from functools import wraps
import psycopg2
from psycopg2 import pool
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_connection")

# Get connection configurations from environment variables
# No real secrets or credentials are hard-coded here.
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 26257))
DB_NAME = os.environ.get("DB_NAME", "defaultdb")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_SSLMODE = os.environ.get("DB_SSLMODE", "disable")

# Threaded connection pool instance
_pool = None

def init_db_pool():
    """Initializes the CockroachDB connection pool."""
    global _pool
    if _pool is None:
        try:
            logger.info(f"Initializing CockroachDB connection pool to {DB_HOST}:{DB_PORT}/{DB_NAME}")
            _pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                sslmode=DB_SSLMODE
            )
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

def get_connection():
    """Retrieves a connection from the pool, initializing it if necessary."""
    if _pool is None:
        init_db_pool()
    return _pool.getconn()

def release_connection(conn):
    """Releases a connection back to the pool."""
    if _pool is not None and conn is not None:
        _pool.putconn(conn)

def close_all_connections():
    """Closes all connections in the pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing all database connections in the pool.")
        _pool.closeall()
        _pool = None

def cockroach_transaction_retry(max_retries=5, backoff_factor=0.1, jitter=True):
    """Decorator to retry query execution on CockroachDB transaction serialization conflicts (40001)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.extensions.TransactionRollbackError) as e:
                    sqlstate = e.pgcode
                    if sqlstate == "40001" and retries < max_retries:
                        retries += 1
                        # Exponential backoff with jitter
                        delay = backoff_factor * (2 ** retries)
                        if jitter:
                            delay = delay * random.uniform(0.5, 1.5)
                        logger.warning(
                            f"Transaction retry (serialization conflict 40001). "
                            f"Attempt {retries}/{max_retries}. Retrying in {delay:.3f}s..."
                        )
                        time.sleep(delay)
                        continue
                    raise
        return wrapper
    return decorator

@cockroach_transaction_retry()
def execute_transaction(func, *args, **kwargs):
    """Executes a function block inside a transaction with connection checkout and automatic retries."""
    conn = get_connection()
    conn.set_session(isolation_level=ISOLATION_LEVEL_SERIALIZABLE)
    try:
        with conn:
            with conn.cursor() as cur:
                result = func(cur, *args, **kwargs)
                return result
    finally:
        release_connection(conn)
