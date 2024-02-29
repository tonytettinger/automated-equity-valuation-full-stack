import json
import sqlite3

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for, make_response
from datetime import datetime
import asyncio
from functions.financial_data_aggregator import *
from functions.settings import get_variables_from_db

from functions.signal_calculator import CalculateSignal
from scheduler.notifications import notify
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
    links = []
    for file in static:
        if file.startswith('index'):
            continue
        if file.endswith('.html'):
            file_without_extension = file[:-5]
            links.append((file, file_without_extension))
    production_html_homepage = render_template('homepage.html', links=links, prod=True)
    development_html_homepage = render_template('homepage.html', links=links, prod=False)
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
    scheduler = request.args.get('scheduler')
    print('scheduler value', scheduler)
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

    response = make_response('Success! Redirecting...', 200)
    # Redirect to another route
    redirect_route = '/signals?scheduler=' + scheduler
    return redirect(redirect_route)


@app.route('/signals', methods=['GET'])
async def signals():
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

    production_html_signals = render_template('signal_page.html',data=financial_data_aggregate,
                           signals=signals, additional_overview_data=ADDITIONAL_OVERVIEW_DATA, prod=True)

    # Write the rendered HTML to the static folder with a timestamp
    try:
        time_string = datetime.today().strftime('%Y-%m-%d')
        static_path_output_html = 'static/' + time_string + '.html'
        with open(static_path_output_html, 'w') as f:
            f.write(production_html_signals)
    except PermissionError as e:
        print('PermissionError creating file:', e)
    except IOError as e:
        print('IOError creating file:', e)

    scheduler = request.args.get('scheduler')
    print('scheduler value in signals endpoint', scheduler)

    if scheduler == 'true':
        notify()

    development_html_signals = render_template('signal_page.html',data=financial_data_aggregate,
                           signals=signals, additional_overview_data=ADDITIONAL_OVERVIEW_DATA, prod=False)
    #return dev version
    return development_html_signals


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
