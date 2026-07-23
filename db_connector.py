"""
db_connector.py
SECTION 2: DATABASE CONNECTOR
Developed by Jenil Pokar | Roll No. 46 | FY AI-DS

Connects the Flask app to MySQL and wraps every stored procedure/function
call defined in 02_mysql_multitenant_procedures_functions_triggers.sql.

Reads its connection settings from environment variables so the same code
works locally and on Render (set these as Render "Environment" variables):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

Uses a small connection pool (not a single shared connection) because a
web app serves multiple requests concurrently -- a single global connection
would not be safe under Flask's threaded request handling.
"""

import os

import mysql.connector
from mysql.connector import pooling
print("DEBUG - DB_HOST IS:", os.environ.get("DB_HOST"))

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "ROOT"),
    "database": os.environ.get("DB_NAME", "asset_management_saas"),
}

_pool = pooling.MySQLConnectionPool(
    pool_name="asset_mgmt_pool",
    pool_size=5,
    **DB_CONFIG,
)


def get_connection():
    return _pool.get_connection()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def run_query(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows
    finally:
        cursor.close()
        conn.close()


def run_write(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        conn.close()


def call_procedure(name, args):
    """Call a procedure with OUT parameters; returns the resolved args list."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        result_args = cursor.callproc(name, args)
        conn.commit()
        return result_args
    finally:
        cursor.close()
        conn.close()


def call_procedure_with_result_set(name, args=()):
    """Call a procedure that ends with a SELECT (sp_list_allocated_assets, etc.)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.callproc(name, args)
        columns, rows = [], []
        for result in cursor.stored_results():
            columns = [c[0] for c in result.description]
            rows = result.fetchall()
        return columns, rows
    finally:
        cursor.close()
        conn.close()


def call_function(name, args):
    placeholders = ", ".join(["%s"] * len(args))
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT {name}({placeholders})", args)
        return cursor.fetchone()[0]
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Exception mapping
# All application-raised MySQL errors use SIGNAL SQLSTATE '45000', which
# mysql-connector surfaces as errno 1644. This wrapper turns that into a
# clean message string for the Flask routes to flash to the user, instead
# of a raw traceback -- this is the "Exception Handling" layer for
# Invalid Asset ID / Duplicate Serial Number / Asset Already Allocated etc.
# ---------------------------------------------------------------------------

def friendly_db_error(exc):
    if isinstance(exc, mysql.connector.Error) and exc.errno == 1644:
        return str(exc.msg)
    return f"Database error: {exc}"
