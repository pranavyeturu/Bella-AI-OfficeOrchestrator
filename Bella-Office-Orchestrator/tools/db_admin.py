import os
import subprocess
import hashlib
import datetime
import psycopg2
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths to the PostgreSQL CLI tools (set in your .env)
PG_DUMP = os.getenv("PG_DUMP_PATH", "pg_dump")
PSQL    = os.getenv("PSQL_PATH",   "psql")

# Database connection parameters
PG = dict(
    host=os.getenv("PG_HOST"),
    dbname=os.getenv("STAGING_DB"),
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASSWORD"),
    port=os.getenv("PG_PORT", 5432),
)

# Directory where snapshots will be stored
SNAPSHOT_DIR = Path(os.getenv("SNAPSHOT_DIR", "/tmp/db_snapshots"))
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Path to your seed SQL script
SEED_SQL = os.getenv("SEED_SQL_PATH")

def _conn():
    return psycopg2.connect(**PG, options="-c search_path=public")

def snapshot_db() -> tuple[str, str]:
    """
    Run pg_dump to snapshot the entire database.
    Returns (path_to_dump_file, sha256_checksum).
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    outfile = SNAPSHOT_DIR / f"{PG['dbname']}_{ts}.sql"
    cmd = [
        PG_DUMP,
        "-h", PG["host"],
        "-U", PG["user"],
        "-p", str(PG["port"]),
        PG["dbname"],
        "-f", str(outfile),
    ]
    # pg_dump reads PGPASSWORD from env
    subprocess.check_call(cmd, env={**os.environ, "PGPASSWORD": PG["password"]})
    sha = hashlib.sha256(outfile.read_bytes()).hexdigest()
    return str(outfile), sha

def wipe_db():
    """Drop and recreate the public schema (everything inside it)."""
    sql = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()

def restore_seed():
    """
    Restore the database by running your seed SQL file via psql.
    """
    cmd = [
        PSQL,
        "-h", PG["host"],
        "-U", PG["user"],
        "-p", str(PG["port"]),
        "-d", PG["dbname"],
        "-f", SEED_SQL,
    ]
    subprocess.check_call(cmd, env={**os.environ, "PGPASSWORD": PG["password"]})

def log_audit(action: str, sha: str, approved_by: str):
    """
    Record the refresh action in the audit_refresh table.
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_refresh (
            id serial PRIMARY KEY,
            action text,
            checksum text,
            approved_by text,
            ts timestamptz DEFAULT now()
        )""")
        cur.execute("""
        INSERT INTO audit_refresh(action, checksum, approved_by)
        VALUES (%s, %s, %s)
        """, (action, sha, approved_by))
        conn.commit()

# Optional helpers if you want table-specific operations:
def drop_table(table_name: str):
    """Drop a single table by name."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS public.{table_name} CASCADE;")
        conn.commit()

def restore_table_from_seed(table_name: str):
    """
    Restore tables from the seed file; here we re-run the entire seed.
    If seed_data.sql contains only the table of interest, it recreates that table.
    """
    restore_seed()
