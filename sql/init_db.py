import sqlite3

try:
    connection = sqlite3.connect('./database.db')

    # Execute the schema script
    with open('schema.sql') as f:
        connection.executescript(f.read())

    # Insert values into the variables table
    cur = connection.cursor()
    cur.execute("INSERT INTO finvars (perpetual_growth_rate, market_return) VALUES (?, ?)", (0.025, 0.1))

    # Commit changes and close connection
    connection.commit()
    connection.close()

    print("Database initialization successful.")
except Exception as e:
    print("Error occurred:", e)
