import json
import sqlite3

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import asyncio
from functions.financial_data_aggregator import *
from functions.settings import get_variables_from_db

from functions.signal_calculator import CalculateSignal
from sql.helpers import database_path, database_access

load_dotenv()

current_year = datetime.now().year

PROJECT_NAME = 'automated-equity-valuation-full-stack'

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
    link_prefix = '/static/'
    # Generate links for each HTML file
    if os.getenv('FLASK_ENV') == 'development':
        link_prefix = '/static/'
    links = []
    prefixed_links = []
    for file in static:
        if file.startswith('index'):
            continue
        if file.endswith('.html'):
            file_without_extension = file[:-5]
            links.append((file, file_without_extension))
            prefixed_links.append((link_prefix+file, file_without_extension))
    production_html_homepage = render_template('homepage.html', links=links)
    development_html_homepage = render_template('homepage_dev_template.html', links=links)
    with open('static/index.html', 'w') as f:
        f.write(production_html_homepage)
    return development_html_homepage


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
            # Remove stock that had an error in processing its data while querying
            symbols.remove(e.exception_variable)

    if len(symbols) == 0:
        raise Exception('No symbols to loop through')
    for symbol in symbols:
        await signal_calculator.do_calculations(symbol, financial_data_aggregator.financial_data_aggregate,
                                          financial_data_aggregator.global_data)

    signals = signal_calculator.get_sorted_dict()
    financial_data_aggregate = financial_data_aggregator.financial_data_aggregate
    # Convert signals to JSON format
    signals_json = json.dumps(signals)

    # Write signals JSON to a file
    try:
        with open('static/signals.json', 'w') as f:
            f.write(signals_json)
        print("Signals saved to signals.json")
    except IOError as e:
        print("Error saving signals to file:", e)

    financial_data_aggregate_json = json.dumps(financial_data_aggregator.financial_data_aggregate)
    # Write signals JSON to a file
    try:
        with open('static/financial_data_aggregate.json', 'w') as f:
            f.write(financial_data_aggregate_json)
        print("Data aggregate saved to financial_data_aggregate.json")
    except IOError as e:
        print("Error saving signals to file:", e)

    rendered_html = render_template('signal_page.html', data=financial_data_aggregator.financial_data_aggregate,
                                    signals=signal_calculator.get_sorted_dict(), additional_overview_data=ADDITIONAL_OVERVIEW_DATA)

    # Write the rendered HTML to the static folder with a timestamp
    try:
        time_string = datetime.today().strftime('%Y-%m-%d')
        static_path_output_html = 'static/' + time_string + '.html'
        with open(static_path_output_html, 'w') as f:
            f.write(rendered_html)
    except PermissionError as e:
        print('PermissionError creating file:', e)
    except IOError as e:
        print('IOError creating file:', e)

    return 'successfully created the html file for financial data.'


@app.route('/signal-page-dev-template', methods=['GET'])
async def show_signals():
    # Read signals data from the file
    try:
        with open('static/signals.json', 'r') as f:
            signals_json = f.read()
            signals = json.loads(signals_json)
        print("Signals loaded from signals.json")
    except FileNotFoundError:
        print("Signals file not found")
    except json.JSONDecodeError as e:
        print("Error decoding signals JSON:", e)

    try:
        with open('static/financial_data_aggregate.json', 'r') as f:
            financial_data_aggregate_json = f.read()
            financial_data_aggregate = json.loads(financial_data_aggregate_json)
        print("Financial data aggregate loaded from financial_data_aggregate.json")
    except FileNotFoundError:
        print("Financial data aggregate file not found")
    except json.JSONDecodeError as e:
        print("Error decoding financial data aggregate JSON:", e)

    return render_template('signal_page.html', data=financial_data_aggregate,
                           signals=signals, additional_overview_data=ADDITIONAL_OVERVIEW_DATA)


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
