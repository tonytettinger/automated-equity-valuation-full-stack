from flask import Flask, render_template
from datetime import datetime
import asyncio
from financial_data_aggregator import *
from collections import defaultdict

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__)


class CalculateSignal:
    def __init__(self):
        self.signals = defaultdict(lambda: defaultdict(dict))

    def get_signal(self):
        return self.signals

    def do_calulations(self, symbol, data):
        total_net_income_periods = list(map(int,data[symbol]['INCOME_STATEMENT']['netIncome']))
        self.calc_fcfe_net_income_ratio(symbol, data, total_net_income_periods)
        self.calc_net_income_margin(symbol, data, total_net_income_periods)

    # Calculate the lowest Free Cash Flow to Equity / Net Income ratio for the time period
    def calc_fcfe_net_income_ratio(self, symbol, data, total_net_income_periods):
        total_cash_flow_periods = list(map(int,data[symbol]['CASH_FLOW']['operatingCashflow']))
        capex_periods = list(map(int,data[symbol]['CASH_FLOW']['capitalExpenditures']))

        fcfe_net_income_ratio = [(total_cash_flow - capex) / total_net_income for total_cash_flow, capex, total_net_income in zip(total_cash_flow_periods,capex_periods,total_net_income_periods)]

        self.signals[symbol]['FCFE_NET_INCOME_RATIO'] = min(fcfe_net_income_ratio)

    def calc_net_income_margin(self, symbol, data, total_net_income_periods):
        total_revenue_periods = list(map(int,data[symbol]['INCOME_STATEMENT']['totalRevenue']))

        net_income_margin = [total_net_income_period / total_revenue_period for total_net_income_period, total_revenue_period in zip(total_net_income_periods, total_revenue_periods)]
        self.signals[symbol]['NET_INCOME_MARGIN'] = min(net_income_margin)


signal_calculator = CalculateSignal()


@app.route('/')
async def main_page_finance_data():
    symbols = ['AAPL']
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    tasks = []
    for function_type in function_types:
        for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
            tasks.append(financial_data_aggregator.get_overview_data(symbol))
            tasks.append(financial_data_aggregator.get_price_data(symbol))
    await asyncio.gather(*tasks)
    for symbol in symbols:
        signal_calculator.do_calulations(symbol, financial_data_aggregator.financial_data_aggregate)
    return render_template('data.html', data=financial_data_aggregator.financial_data_aggregate,
                           calcs=signal_calculator.get_signal())


if __name__ == '__main__':
    app.run()
