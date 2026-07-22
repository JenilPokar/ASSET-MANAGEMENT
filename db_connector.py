"""
db_connector.py
Connection layer between the Tkinter GUI and the MySQL database created by
01_mysql_schema_and_data.sql / 02_mysql_procedures_functions_triggers.sql.

Uses mysql-connector-python (pip install mysql-connector-python).
Kept separate from the GUI code so the front-end never has to know how a
connection is obtained -- it just calls these functions.
"""

import mysql.connector
from mysql.connector import Error as MySQLError

# ---------------------------------------------------------------------------
# Update these to match your MySQL Workbench connection before running.
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "ROOT",
    "database": "asset_management",
}

_connection = None  # module-level singleton so the whole app shares one link


def get_connection():
    """Return a live MySQL connection, reconnecting if it has dropped."""
    global _connection
    if _connection is None or not _connection.is_connected():
        _connection = mysql.connector.connect(**DB_CONFIG)
    return _connection


def run_query(sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    """Run a SELECT and return (column_names, rows)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return columns, rows
    finally:
        cursor.close()


def run_write(sql: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the number of affected rows."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()


def call_procedure(name: str, args: list) -> list:
    """
    Call a stored procedure. `args` should include placeholder values for
    OUT parameters (e.g. 0 or None) -- mysql-connector resolves their final
    values and returns them via cursor.stored_results() / cursor.fetchall()
    depending on the procedure. This helper returns the OUT-parameter values
    read back from MySQL session variables, which is the standard pattern
    for mysql-connector-python.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        result_args = cursor.callproc(name, args)
        conn.commit()
        return result_args
    finally:
        cursor.close()


def call_procedure_with_result_set(name: str, args: tuple = ()) -> tuple[list[str], list[tuple]]:
    """Call a stored procedure that returns a SELECT result set (e.g. sp_list_allocated_assets)."""
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


def call_function(name: str, args: tuple) -> object:
    """Call a scalar-returning stored FUNCTION via a SELECT wrapper."""
    placeholders = ", ".join(["%s"] * len(args))
    sql = f"SELECT {name}({placeholders})"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, args)
        return cursor.fetchone()[0]
    finally:
        cursor.close()


def close_connection():
    global _connection
    if _connection is not None and _connection.is_connected():
        _connection.close()
    _connection = None
