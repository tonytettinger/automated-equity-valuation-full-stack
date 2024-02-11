from flask import Flask, render_template
from datetime import datetime
import asyncio
from financial_data_aggregator import *

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__)


@app.route('/')
async def main_page_finance_data():
    symbols = ['AAPL', 'META', 'IBM']
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    tasks = []
    for function_type in function_types:
        for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
            tasks.append(financial_data_aggregator.get_overview_data(symbol))
            tasks.append(financial_data_aggregator.get_price_data(symbol))
    await asyncio.gather(*tasks)
    return render_template('data.html', data=financial_data_aggregator.financial_data_aggregate)


if __name__ == '__main__':
    app.run()
