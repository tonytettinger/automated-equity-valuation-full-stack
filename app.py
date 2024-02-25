import sqlite3

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect
from datetime import datetime
import asyncio
from functions.financial_data_aggregator import *
from functions.settings import get_variables_from_db

from functions.signal_calculator import CalculateSignal
from sql.helpers import database_path, database_access

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__, static_url_path='/static')
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

signal_calculator = CalculateSignal()


def get_html_files(folder):
    html_files = [file for file in os.listdir(folder) if file.endswith('.html')]
    return html_files


@app.errorhandler(Exception)
def handle_global_error(error):
    # Handle the error and return an appropriate response
    response = {
        'error': 'An unexpected error occurred',
        'message': str(error)
    }
    return jsonify(response), 500


@app.route('/')
def index():
    static = os.listdir('static')

    # Generate links for each HTML file
    links = []
    for file in static:
        if file.endswith('.html'):
            links.append(f'<a href="./{file}">{file}</a>')

    homepage_rendered_html = render_template('home.html', links=links)
    with open('static/index.html', 'w') as f:
        f.write( homepage_rendered_html)
    return  homepage_rendered_html


async def process_symbols(function_type, symbols):
    tasks = []
    for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
            tasks.append(financial_data_aggregator.get_overview_data(symbol))
            tasks.append(financial_data_aggregator.get_price_data(symbol))
            tasks.append(financial_data_aggregator.get_treasury_data())

    await asyncio.gather(*tasks)


@app.route('/check_stocks', methods=['GET'])
@limiter.limit("30 per minute")
async def main_page_finance_data():
    symbols = ['AAPL', 'SSYS', 'HPQ']
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    tasks = []
    for function_type in function_types:
        try:
            await process_symbols(function_type, symbols)
        except Exception as e:
            print(f"An error occurred: {e}")
            symbols.remove(e.exception_variable)
    print('symbols to loop through:', symbols )

    if len(symbols) == 0:
        raise Exception('No symbols to loop through')
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


@app.route('/settings', methods=['GET'])
def settings():
    columns, values = get_variables_from_db()
    column_value_zip = zip(columns, values)
    return render_template('settings.html', columns=columns, values=values, column_value_zip=column_value_zip)


@app.route('/update_value', methods=['POST'])
def update_value():
    database_access.update_selected_value()
    return redirect('/settings')


if __name__ == '__main__':
    app.run()
