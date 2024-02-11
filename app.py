from flask import Flask, render_template
from datetime import datetime
import asyncio
from financial_data_aggregator import *
from collections import defaultdict

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__)

#Return percentage differences, if the value would be negative we just take the maximum value
def calculate_percentage_difference(array):
    percentage_differences = []
    for i in range(len(array) - 1):
        current_element = array[i]
        next_element = array[i + 1]
        percentage_difference = ((next_element - current_element) / current_element)
        percentage_differences.append(percentage_difference)
        average = sum(percentage_differences) / len(percentage_differences)
        if average <= 0:
            return max(percentage_differences)
        else:
            return average

def calculate_growth(initial_value, growth_rate, periods):
    print(initial_value)
    print(growth_rate)
    print(periods)
    return [initial_value * (1 + growth_rate) ** n for n in range(1, periods + 1)]

class CalculateSignal:
    def __init__(self):
        self.signals = defaultdict(lambda: defaultdict(dict))

    def get_signal(self):
        return self.signals

    def do_calulations(self, symbol, data):
        total_net_income_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['netIncome']))
        total_revenue_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['totalRevenue']))
        self.calc_fcfe_net_income_ratio(symbol, data, total_net_income_periods)
        self.calc_net_income_margin(symbol, data, total_net_income_periods)
        self.calc_earnings_growth(symbol, total_net_income_periods)
        self.calc_projected_free_cash_flow(symbol, total_revenue_periods, 4)
    # Calculate the average Free Cash Flow to Equity / Net Income ratio for the time period
    def calc_fcfe_net_income_ratio(self, symbol, data, total_net_income_periods):
        total_cash_flow_periods = list(map(int, data[symbol]['CASH_FLOW']['operatingCashflow']))
        capex_periods = list(map(int, data[symbol]['CASH_FLOW']['capitalExpenditures']))

        fcfe_net_income_ratio = [(total_cash_flow - capex) / total_net_income for
                                 total_cash_flow, capex, total_net_income in
                                 zip(total_cash_flow_periods, capex_periods, total_net_income_periods)]

        self.signals[symbol]['FCFE_NET_INCOME_RATIO'] = sum(fcfe_net_income_ratio) / len(fcfe_net_income_ratio)

    # Calculate the net income margin and take the minimum for the most conservative estimate
    def calc_net_income_margin(self, symbol, data, total_net_income_periods):
        total_revenue_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['totalRevenue']))

        net_income_margin = [total_net_income_period / total_revenue_period for
                             total_net_income_period, total_revenue_period in
                             zip(total_net_income_periods, total_revenue_periods)]
        self.signals[symbol]['NET_INCOME_MARGIN'] = min(net_income_margin) + 1

    def calc_earnings_growth(self, symbol, total_net_income_periods):
        self.signals[symbol]['EARNINGS_GROWTH_RATE'] = calculate_percentage_difference(total_net_income_periods)

    def calc_projected_free_cash_flow(self, symbol, total_revenue_periods, period):
        projected_revenue = calculate_growth(total_revenue_periods[-1], self.signals[symbol]['EARNINGS_GROWTH_RATE'], period)
        projected_net_income = [self.signals[symbol]['NET_INCOME_MARGIN'] * revenue for revenue in projected_revenue]
        projected_free_cash_flows = [self.signals[symbol]['FCFE_NET_INCOME_RATIO'] * net_income for net_income in projected_net_income]
        self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'] = projected_free_cash_flows



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
