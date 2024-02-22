import sqlite3
from flask import request

from sql.helpers import database_path


def update_value():
    new_value = request.form['new_value']
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    # Update the SQL value
    cursor.execute("UPDATE finvars SET market_return = ?", (new_value,))
    conn.commit()
    conn.close()