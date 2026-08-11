#!/usr/bin/env python
import os
import sys
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("health_check")

# Load environment configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 26257))
DB_NAME = os.environ.get("DB_NAME", "defaultdb")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_SSLMODE = os.environ.get("DB_SSLMODE", "disable")

def run_health_check():
    """Performs database health checks."""
    logger.info(f"Connecting to database at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=DB_SSLMODE,
            connect_timeout=3
        )
        with conn.cursor() as cur:
            # 1. Ping the database
            cur.execute("SELECT 1;")
            val = cur.fetchone()[0]
            if val != 1:
                logger.error("Ping failed: returned incorrect result.")
                return 1
            logger.info("Ping successful.")
            
            # 2. Check schema table existence
            cur.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name IN ('users', 'incidents', 'solution_attempts');
                """
            )
            tables = [row[0] for row in cur.fetchall()]
            required_tables = {'users', 'incidents', 'solution_attempts'}
            missing = required_tables - set(tables)
            if missing:
                logger.error(f"Healthy check failed: Schema is missing tables: {missing}")
                return 2
            
            logger.info("Schema integrity verified. All tables present.")
            
        logger.info("Database and system health is OK.")
        return 0
    except Exception as e:
        logger.error(f"Health check failed: Unable to connect to CockroachDB: {e}")
        return 3
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    sys.exit(run_health_check())
