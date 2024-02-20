import sqlite3

from sql.helpers import database_path


def get_variables_from_db():
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(finvars)")
    # All variables from the database
    columns = [row[1] for row in cursor.fetchall()]
    # Fetch the first row of data from the table
    cursor.execute(f"SELECT * FROM finvars LIMIT 1")
    values = cursor.fetchone()

    return columns, values
