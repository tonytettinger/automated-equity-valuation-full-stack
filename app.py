from flask import Flask, jsonify, render_template
import requests
from datetime import datetime

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

    def add_to_financial_data_aggregate(self, key, value):
        self.financial_data_aggregate[key] = value

    def get_financial_data_aggregate(self):
        return self.financial_data_aggregate

    def process_data(self, data_type, data):
        default = "Incorrect data"

        return getattr(self, str(data_type).lower(), lambda: default)(data)

    def cash_flow(self, data):
        cash_flow_keys = ['operatingCashflow', 'capitalExpenditures']

        operating_cash_flows = create_empty_dict(cash_flow_keys)
        for idx in self.year_range:
            current_year_data = data['annualReports'][idx]
            add_years_data(operating_cash_flows, current_year_data)

        self.add_to_financial_data_aggregate('operating_cash_flows', operating_cash_flows)


financial_data_aggregator = FinancialDataTypeSwitch()


@app.route('/')
def get_cash_flow():
    api_key = 'YOQ67R5EHDTUAZFW'
    function_type = 'CASH_FLOW'
    symbol = 'META'

    api_url = f'https://www.alphavantage.co/query?function={function_type}&symbol={symbol}&apikey={api_key}'
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()

        financial_data_aggregator.process_data(function_type, data)

        return render_template('data.html', data=financial_data_aggregator.financial_data_aggregate)
    else:
        return jsonify({'error': 'Failed to fetch weather data'})


if __name__ == '__main__':
    app.run()
