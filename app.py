from flask import Flask, render_template
from datetime import datetime
import asyncio
from functions.financial_data_aggregator import *

from functions.signal_calculator import CalculateSignal

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__, static_url_path='/static')

signal_calculator = CalculateSignal()


@app.route('/')
async def main_page_finance_data():
    symbols = ['SSYS']
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    tasks = []
    for function_type in function_types:
        for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
            tasks.append(financial_data_aggregator.get_overview_data(symbol))
            tasks.append(financial_data_aggregator.get_price_data(symbol))
            tasks.append(financial_data_aggregator.get_treasury_data())
    await asyncio.gather(*tasks)
    for symbol in symbols:
        signal_calculator.do_calculations(symbol, financial_data_aggregator.financial_data_aggregate,
                                          financial_data_aggregator.global_data)
    rendered_html = render_template('data.html', data=financial_data_aggregator.financial_data_aggregate,
                           signals=signal_calculator.get_sorted_dict())

    # Write the rendered HTML to a file
    try:
        time_string = datetime.today().strftime('%Y-%m-%d')
        static_path_output_html = 'static/' + time_string + '.html'
        with open('index.html', 'w') as f:
            f.write(rendered_html)
        with open(static_path_output_html, 'w') as f:
            f.write(rendered_html)
    except PermissionError as e:
        print('PermissionError creating file:', e)
    except IOError as e:
        print('IOError creating file:', e)

    return rendered_html


if __name__ == '__main__':
    app.run()
