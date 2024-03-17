import json
import sqlite3

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for, make_response
from datetime import datetime
import asyncio

from functions.additional_tickers import get_tech_stock_market_movers, get_biggest_losers
from functions.financial_data_aggregator import *
from functions.get_links_from_static import get_links_from_static
from functions.settings import get_variables_from_db

from functions.signal_calculator import CalculateSignal
from scheduler.github import add_all_in_static_and_commit
from scheduler.notifications import notify_slack_channel
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
    links = get_links_from_static()
    development_html_homepage = render_template('homepage.html', links=links, prod=False)

    return development_html_homepage


async def get_datatypes_for_symbols(function_type, stock_symbols):
    tasks = []
    for ticker in stock_symbols:
        tasks.append(financial_data_aggregator.get_data(function_type, ticker))

    await asyncio.gather(*tasks)


async def get_generic_symbol_data(symbols):
    tasks = []
    for symbol in symbols:
        tasks.append(financial_data_aggregator.get_overview_data(symbol))
        tasks.append(financial_data_aggregator.get_price_data(symbol))

    await asyncio.gather(*tasks)


async def get_market_data():
    return await financial_data_aggregator.get_treasury_data()


def remove_non_alphanumeric(strings):
    return [''.join(char for char in string if char.isalnum()) for string in strings]


async def get_biggest_movers_and_losers_symbols():
    # Perform some asynchronous task
    api_url = f'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={os.getenv("ALPHA_VANTAGE_API_KEY")}'
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        if len(data) == 0:
            return []
        else:
            most_traded = [entry["ticker"] for entry in data["most_actively_traded"]]
            top_losers = [entry["ticker"] for entry in data["top_losers"]]
            combined_array_most_traded_and_top_losers = list(set(most_traded + top_losers))
            cleaned_combined_array = remove_non_alphanumeric(combined_array_most_traded_and_top_losers)
            print('cleaned_combined_array', cleaned_combined_array)
            return cleaned_combined_array
    else:
        print('additional tickers not found')
        return []


@app.route('/check_stocks', methods=['GET'])
@limiter.limit("20 per minute")
async def main_page_finance_data():
    base_symbols = ['MTCH', 'PYPL']
    market_movers = await get_tech_stock_market_movers()
    biggest_losers = await get_biggest_losers()
    print('biggest losers are')
    symbols = list(set(base_symbols + market_movers + biggest_losers))
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    scheduler = request.args.get('scheduler')
    if not scheduler:
        scheduler = ''
    for function_type in function_types:
        await get_datatypes_for_symbols(function_type, symbols)

    print('symbols to remove due to errors in querying', financial_data_aggregator.symbols_to_remove)
    symbols = [symbol for symbol in symbols if symbol not in financial_data_aggregator.symbols_to_remove]

    await get_generic_symbol_data(symbols)
    print('generic symbol data for symbols successfully queried:', symbols)
    await get_market_data()
    print('market data successfully queried for symbols', symbols)
    if len(symbols) == 0:
        raise Exception('No symbols to loop through')
    for symbol in symbols:
        await signal_calculator.do_calculations(symbol, financial_data_aggregator.financial_data_aggregate,
                                                financial_data_aggregator.global_data)

    signals = signal_calculator.get_sorted_dict()
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

    links = get_links_from_static()
    print('links are', links)
    production_html_homepage = render_template('homepage.html', links=links, prod=True)
    try:
        with open('static/index.html', 'w') as f:
            f.write(production_html_homepage)
        print('generated index.html file')
    except IOError as e:
        print("Error generating index.html file:", e)

    print('scheduler is: ', scheduler)
    # Redirect to another route
    if scheduler != '':
        redirect_route = '/signals?scheduler=' + scheduler
        print('redirect route with scheduler', scheduler)
    else:
        redirect_route = '/signals'
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

    production_html_signals = render_template('signal_page.html', data=financial_data_aggregate,
                                              signals=signals, additional_overview_data=ADDITIONAL_OVERVIEW_DATA,
                                              prod=True)

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
        signal_keys = signals.keys()  # Get all the keys from the dictionary
        if signal_keys:  # Check if the keys are not empty
            print("The signals dictionary has tickers.")
            print("The signal keys are:", signal_keys)
            add_all_in_static_and_commit()
            notify_slack_channel(signal_keys)


    development_html_signals = render_template('signal_page.html', data=financial_data_aggregate,
                                               signals=signals, additional_overview_data=ADDITIONAL_OVERVIEW_DATA,
                                               prod=False)
    # return dev version
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
