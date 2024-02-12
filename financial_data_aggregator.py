from flask import jsonify
import requests
from dotenv import load_dotenv
import os

load_dotenv()


def create_empty_dict(keys_array):
    return {key: [] for key in keys_array}


def add_years_data(financial_data_type, current_year_data):
    for key in financial_data_type.keys():
        financial_data_type[key].append(current_year_data[key])


def get_sub_category_data(*, data, year_range, keys):
    sub_category_dict = create_empty_dict(keys)
    for idx in year_range:
        current_year_data = data['annualReports'][idx]
        add_years_data(sub_category_dict, current_year_data)
    return sub_category_dict


class FinancialDataTypeSwitch:
    def __init__(self):
        self.financial_data_aggregate = {}
        # For 4 years data
        self.year_range = range(4)
        self.errorState = []
        self.current_company = None
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

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
        api_url = f'https://www.alphavantage.co/query?function={function_type}&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        self.set_current_company(symbol)
        if response.status_code == 200:
            data = response.json()
            self.process_data(function_type, data)
        else:
            error = jsonify({'error': f'Failed to fetch {function_type} data for {symbol}'})
            self.add_error_to_error_state(error)

    async def get_overview_data(self, symbol):
        api_url = f'https://www.alphafvantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            self.add_to_financial_data_aggregate('BETA', data['Beta'])
            self.add_to_financial_data_aggregate('MARKET_CAPITALIZATION', data['MarketCapitalization'])
        else:
            error = jsonify({'error': f'Failed to fetch overview data for {symbol}'})
            self.add_error_to_error_state(error)

    async def get_price_data(self, symbol):
        api_url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            latest_daily_price_date, latest_daily_price = next(iter(data["Time Series (Daily)"].items()))
            self.add_to_financial_data_aggregate('LATEST_PRICE', latest_daily_price["4. close"])
            self.add_to_financial_data_aggregate('LATEST_PRICE_DATE', latest_daily_price_date)
        else:
            error = jsonify({'error': f'Failed to fetch overview data for {symbol}'})
            self.add_error_to_error_state(error)

    async def get_treasury_data(self, symbol):
        api_url = f'https://www.alphavantage.co/query?function=TREASURY_YIELD&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            self.add_to_financial_data_aggregate('TREASURY_YIELD_10_YEARS', )
        else:
            error = jsonify({'error': f'Failed to fetch treasury data for {symbol}'})
            self.add_error_to_error_state(error)

    def process_data(self, function_type, data):
        default = "Incorrect data"

        return getattr(self, str(function_type).lower(), lambda: default)(data)

    def cash_flow(self, data):
        keys = ['operatingCashflow', 'capitalExpenditures']
        get_sub_category_data(data=data, year_range=self.year_range, keys=keys)

        self.add_to_financial_data_aggregate('CASH_FLOW',
                                             get_sub_category_data(data=data, year_range=self.year_range, keys=keys))

    def income_statement(self, data):
        keys = ['totalRevenue', 'netIncome', 'incomeBeforeTax', 'interestAndDebtExpense', 'incomeTaxExpense', 'interestExpense']
        get_sub_category_data(data=data, year_range=self.year_range, keys=keys)
        self.add_to_financial_data_aggregate('INCOME_STATEMENT',
                                             get_sub_category_data(data=data, year_range=self.year_range, keys=keys))

    def balance_sheet(self, data):
        keys = ['commonStockSharesOutstanding','shortLongTermDebtTotal']
        get_sub_category_data(data=data, year_range=self.year_range, keys=keys)
        self.add_to_financial_data_aggregate('BALANCE_SHEET',
                                             get_sub_category_data(data=data, year_range=self.year_range, keys=keys))


financial_data_aggregator = FinancialDataTypeSwitch()
