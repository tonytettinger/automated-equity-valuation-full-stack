import sqlite3
from flask import request
def update_database():
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Fetch column names from a specific table (change 'your_table_name' to your table name)
    cursor.execute("PRAGMA table_info(finvars)")
    columns = [row[1] for row in cursor.fetchall()]