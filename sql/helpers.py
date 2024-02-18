import os
import sqlite3
from enum import Enum

current_directory = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(current_directory, 'database.db')

class FinancialVars(Enum):
    perpetual_growth_rate = 'perpetual_growth_rate'
    market_rate = 'market_return'

def get_data():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    financial_variables = conn.execute('SELECT * FROM finvars').fetchall()
    conn.close()
    return financial_variables

class DatabaseAccess:
    def __init__(self):
        self.data  = get_data()
    def get_perpetual_growth(self):
        return self.data[0][FinancialVars.perpetual_growth_rate.value]
    def get_market_rate(self):
        return self.data[0][FinancialVars.market_rate.value]

database_access = DatabaseAccess()

print(database_access.get_perpetual_growth())