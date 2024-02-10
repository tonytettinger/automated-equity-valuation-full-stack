from flask import Flask, jsonify, render_template
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import asyncio



load_dotenv()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


current_year = datetime.now().year

app = Flask(__name__)


def create_empty_dict(keys_array):
    return {key: [] for key in keys_array}


def add_years_data(financial_data_type, current_year_data):
    for key in financial_data_type.keys():
        financial_data_type[key].append(current_year_data[key])


class FinancialDataTypeSwitch:
    def __init__(self):
        self.financial_data_aggregate = {}
        # For 4 years data
        self.year_range = range(4)
        self.errorState = []
        self.current_company = None

    def add_error_to_error_state(self, error):
        self.errorState.append(error)

    def set_current_company(self, company):
        self.current_company = company

    def add_to_financial_data_aggregate(self, key, value):
        if self.current_company not in self.financial_data_aggregate:
            self.financial_data_aggregate[self.current_company] = {}
        self.financial_data_aggregate[self.current_company][key] = value

    def get_financial_data_aggregate(self):
        return self.financial_data_aggregate

    async def get_data(self, function_type, symbol):
        api_key = ALPHA_VANTAGE_API_KEY
        api_url = f'https://www.alphavantage.co/query?function={function_type}&symbol={symbol}&apikey={api_key}'
        response = requests.get(api_url)
        self.set_current_company(symbol)
        if response.status_code == 200:
            data = response.json()
            self.process_data(function_type, data)
        else:
            error = jsonify({'error': f'Failed to fetch {function_type} data for {symbol}'})
            self.add_error_to_error_state(error)

    def process_data(self, function_type, data):
        default = "Incorrect data"

        return getattr(self, str(function_type).lower(), lambda: default)(data)

    def cash_flow(self, data):
        cash_flow_keys = ['operatingCashflow', 'capitalExpenditures']

        operating_cash_flows = create_empty_dict(cash_flow_keys)
        for idx in self.year_range:
            current_year_data = data['annualReports'][idx]
            add_years_data(operating_cash_flows, current_year_data)

        self.add_to_financial_data_aggregate('operating_cash_flows', operating_cash_flows)


financial_data_aggregator = FinancialDataTypeSwitch()


@app.route('/')
async def get_stuff():
    data = 'None'
    symbols = ['AAPL', 'META', 'IBM']
    function_types = ['CASH_FLOW']
    tasks = []
    for function_type in function_types:
        for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
    await asyncio.gather(*tasks)
    return render_template('data.html', data=financial_data_aggregator.financial_data_aggregate)

if __name__ == '__main__':
    app.run()
