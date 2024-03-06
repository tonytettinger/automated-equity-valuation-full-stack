from flask import jsonify
import requests
from dotenv import load_dotenv
import os

from functions.helpers import CustomException

load_dotenv()

ADDITIONAL_OVERVIEW_DATA = [
    ('Description', 'Company description'),
    ('52WeekHigh', '52 week high'),
    ('52WeekLow', '52 week low'),  # Converted to tuple format
    ('AnalystTargetPrice', 'Analyst target price'),  # Converted to tuple format
    ('PERatio', 'PE ratio'),  # Converted to tuple format
    ('ForwardPE', 'Forward PE'),  # Converted to tuple format
    ('ProfitMargin', 'Profit margin'),  # Converted to tuple format
    ('PriceToSalesRatioTTM', 'Price to sales ratio (TTM)'),  # Converted to tuple format
    ('PriceToBookRatio', 'Price to book ratio')  # Converted to tuple format
]

def create_empty_dict(keys_array):
    return {key: [] for key in keys_array}


def add_years_data(sub_category_dict, current_year_data):
    for key in sub_category_dict.keys():
        if current_year_data[key] == 'None':
            sub_category_dict[key].append(0)
        else:
            sub_category_dict[key].append(int(current_year_data[key]))





class FinancialDataTypeSwitch:
    def __init__(self):
        self.financial_data_aggregate = {}
        self.symbols_to_remove = []
        self.global_data = {}
        # For 4 years data
        self.year_range = range(4)
        self.current_company = None
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    def get_sub_category_data(self, *, data, year_range, keys):
        sub_category_dict = create_empty_dict(keys)
        for idx in year_range:
            try:
                current_year_data = data['annualReports'][idx]
                add_years_data(sub_category_dict, current_year_data)
            except:
                print("removing symbol because of error in getting sub-category",)
                self.add_symbols_to_remove(self.current_company)
                continue
        return sub_category_dict

    def add_symbols_to_remove(self, current_company):
        self.symbols_to_remove.append(current_company)

    def set_current_company(self, company):
        self.current_company = company

    def add_to_financial_data_aggregate(self, key, value):
        try:
            if self.current_company not in self.financial_data_aggregate:
                self.financial_data_aggregate[self.current_company] = {}
            if value != 'None' or value != '':
                self.financial_data_aggregate[self.current_company][key] = value
            else:
                print('company', self.current_company, 'removed from queried companies in add_to_financial_data_aggregate')
                self.add_symbols_to_remove(self.current_company)
        except:
            print("error in adding data to financial", key, value)

    def get_financial_data_aggregate(self):
        return self.financial_data_aggregate

    def get_global_data(self):
        return self.global_data

    async def get_data(self, function_type, symbol):
        api_url = f'https://www.alphavantage.co/query?function={function_type}&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        self.set_current_company(symbol)
        if response.status_code == 200:
            data = response.json()
            if len(data) == 0:
                print('data in financial aggregator is empty for', symbol)
                self.add_symbols_to_remove(symbol)
                print(f"Stock {symbol} returned an empty dictionary response", symbol)
            else:
                print('checking stock', symbol)
                print('with function_type', function_type)
                self.process_data(function_type, data)
        else:
            error = jsonify({'error': f'Failed to fetch {function_type} data for {symbol}'})
            print(error)
            print('removing stock in get_data', symbol)
            self.add_symbols_to_remove(symbol)

    async def get_overview_data(self, symbol):
        api_url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        self.current_company = symbol
        print('getting overview data')
        if response.status_code == 200:
            data = response.json()
            self.add_to_financial_data_aggregate('BETA', data['Beta'])
            print('market CAPITALIZATION is ', data['MarketCapitalization'])
            print('current aggregate for ', symbol, ' is ', self.financial_data_aggregate)
            self.add_to_financial_data_aggregate('MARKET_CAPITALIZATION', data['MarketCapitalization'])
            for key, value in ADDITIONAL_OVERVIEW_DATA:
                self.add_to_financial_data_aggregate(key, data[key])

        else:
            self.add_symbols_to_remove(symbol)

    async def get_price_data(self, symbol):
        try:
            api_url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={self.api_key}'
            response = requests.get(api_url)
            self.current_company = symbol
            if response.status_code == 200:
                data = response.json()
                latest_daily_price_date, latest_daily_price = next(iter(data["Time Series (Daily)"].items()))
                self.add_to_financial_data_aggregate('LATEST_PRICE', latest_daily_price["4. close"])
                self.add_to_financial_data_aggregate('LATEST_PRICE_DATE', latest_daily_price_date)
            else:
                print('removing symbol due to failed to get price data')
                self.add_symbols_to_remove(symbol)
        except:
            print('removing symbol due to failed to get price data')
            self.add_symbols_to_remove(symbol)

    async def get_treasury_data(self):
        api_url = f'https://www.alphavantage.co/query?function=TREASURY_YIELD&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            self.global_data['TREASURY_YIELD'] = data['data'][0]['value']
        else:
            error = jsonify({'error': f'Failed to fetch treasury data'})
            raise Exception(error)

    def process_data(self, function_type, data):
        default = "Incorrect data"
        try:
            print('processing data')
            return getattr(self, str(function_type).lower(), lambda: default)(data)
        except:
            raise Exception(f"{function_type} processing had an error (process_data)")

    def cash_flow(self, data):
        keys = ['operatingCashflow', 'capitalExpenditures']

        self.add_to_financial_data_aggregate('CASH_FLOW',
                                             self.get_sub_category_data(data=data, year_range=self.year_range, keys=keys))

    def income_statement(self, data):
        keys = ['totalRevenue', 'netIncome', 'incomeBeforeTax', 'interestAndDebtExpense', 'incomeTaxExpense', 'interestExpense']
        self.add_to_financial_data_aggregate('INCOME_STATEMENT',
                                             self.get_sub_category_data(data=data, year_range=self.year_range, keys=keys))

    def balance_sheet(self, data):
        keys = ['commonStockSharesOutstanding','shortTermDebt', 'longTermDebt']
        self.add_to_financial_data_aggregate('BALANCE_SHEET',
                                             self.get_sub_category_data(data=data, year_range=self.year_range, keys=keys))


financial_data_aggregator = FinancialDataTypeSwitch()
