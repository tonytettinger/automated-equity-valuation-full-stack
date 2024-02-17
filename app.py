from operator import getitem

from flask import Flask, render_template
from datetime import datetime
import asyncio
from financial_data_aggregator import *
from collections import defaultdict, OrderedDict

load_dotenv()

current_year = datetime.now().year

app = Flask(__name__)

# Percentage of market return rate estimate
MARKET_RETURN_RATE = 0.1

# Perpetual growth estimate

PERPETUAL_GROWTH_ESTIMATE = 0.025


# Return percentage differences, if the value would be negative we just take the maximum value
def calculate_percentage_difference(array):
    percentage_differences = []
    for i in range(len(array) - 1):
        current_element = array[i]
        next_element = array[i + 1]
        percentage_difference = ((next_element - current_element) / current_element)
        percentage_differences.append(percentage_difference)
    print('percentage_differences:', percentage_differences)
    average = sum(percentage_differences) / len(percentage_differences)
    print('average:', average)
    if average <= 0:
        maxDif = max(percentage_differences)
        if maxDif < 0:
            return 0
        else:
            return max(percentage_differences)
    else:
        return average


def calculate_growth(initial_value, growth_rate, periods):
    return [initial_value * (1 + growth_rate) ** n for n in range(1, periods + 1)]


def generate_interest_rates(return_multiplier, total_periods):
    rates = [return_multiplier]
    for _ in range(1, total_periods):
        next_rate = rates[-1] * return_multiplier
        rates.append(next_rate)
    rates.append(rates[-1])
    print('rates',rates)
    return rates

def get_nested_value(symbol, dict):
    return dict[symbol]["nested_value"]

class CalculateSignal:
    def __init__(self):
        self.sortedSignals = {}
        self.signals = defaultdict(lambda: defaultdict(dict))

    def get_signal(self):
        return self.signals

    def get_sorted_dict(self):
        return self.sortedSignals['MARKET_CAP']

    def add_sorted_dict_by_category(self, category):
        self.sortedSignals[category] = OrderedDict(sorted(self.signals.items(),
       key = lambda x: getitem(x[1], 'MARKET_CAP')))

    def do_calculations(self, symbol, data, global_data):
        total_net_income_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['netIncome']))
        total_revenue_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['totalRevenue']))
        period_number = len(total_net_income_periods)
        total_debt = int(data[symbol]['BALANCE_SHEET']['shortTermDebt'][0]) + int(data[symbol]['BALANCE_SHEET']['longTermDebt'][0])

        self.calc_fcfe_net_income_ratio(symbol, data, total_net_income_periods)
        self.calc_net_income_margin(symbol, total_net_income_periods, total_revenue_periods)
        self.calc_earnings_growth(symbol, total_revenue_periods)
        self.calc_projected_free_cash_flow(symbol, total_revenue_periods, 4)
        self.calc_wacc(data, symbol, global_data, total_debt)
        self.calc_terminal_value(symbol)
        self.calc_dfc(symbol, period_number,data)
        self.add_sorted_dict_by_category('MARKET_CAP')

    # Calculate the average Free Cash Flow to Equity / Net Income ratio for the time period
    def calc_fcfe_net_income_ratio(self, symbol, data, total_net_income_periods):
        total_cash_flow_periods = list(map(int, data[symbol]['CASH_FLOW']['operatingCashflow']))
        capex_periods = list(map(int, data[symbol]['CASH_FLOW']['capitalExpenditures']))

        fcfe_net_income_ratio = [(total_cash_flow - capex) / total_net_income for
                                 total_cash_flow, capex, total_net_income in
                                 zip(total_cash_flow_periods, capex_periods, total_net_income_periods)]

        self.signals[symbol]['FCFE_NET_INCOME_RATIO'] = sum(fcfe_net_income_ratio) / len(fcfe_net_income_ratio)

    # Calculate the net income margin and take the minimum for the most conservative estimate
    def calc_net_income_margin(self, symbol, total_net_income_periods, total_revenue_periods):

        net_income_margin = [total_net_income_period / total_revenue_period for
                             total_net_income_period, total_revenue_period in
                             zip(total_net_income_periods, total_revenue_periods)]
        print('net_income_margin:', net_income_margin)
        self.signals[symbol]['NET_INCOME_MARGIN'] = min(net_income_margin)

    def calc_earnings_growth(self, symbol, total_revenue_periods):
        self.signals[symbol]['EARNINGS_GROWTH_RATE'] = calculate_percentage_difference(total_revenue_periods)

    def calc_projected_free_cash_flow(self, symbol, total_revenue_periods, period):
        print('growth_rate', self.signals[symbol]['EARNINGS_GROWTH_RATE'])
        print('revenue_basic', total_revenue_periods[0])
        projected_revenue = calculate_growth(total_revenue_periods[0], self.signals[symbol]['EARNINGS_GROWTH_RATE'],
                                             period)
        print('projected_revenue', projected_revenue)
        projected_net_income = [self.signals[symbol]['NET_INCOME_MARGIN'] * revenue for revenue in projected_revenue]
        print('projected_net_income', projected_net_income)
        projected_free_cash_flows = [self.signals[symbol]['FCFE_NET_INCOME_RATIO'] * net_income for net_income in
                                     projected_net_income]
        print('projected_fcf', projected_free_cash_flows)
        self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'] = projected_free_cash_flows

    def calc_effective_tax_rate(self, data, symbol):
        income_before_tax_latest = int(data[symbol]['INCOME_STATEMENT']['incomeBeforeTax'][0])
        income_tax_expense_latest = int(data[symbol]['INCOME_STATEMENT']['incomeTaxExpense'][0])
        if income_tax_expense_latest <= 0:
            return 0
        else:
            return abs(income_tax_expense_latest / income_before_tax_latest)

    def calc_debt_cost_wacc(self, data, symbol,total_debt):
        interest_expense = data[symbol]['INCOME_STATEMENT']['interestExpense'][0]
        return float(interest_expense) / float(total_debt)

    def calc_equity_cost(self, data, symbol, global_data):
        treasury_yield = float(global_data['TREASURY_YIELD']) * 0.01
        print('treasury yield:', treasury_yield)
        beta = float(data[symbol]['BETA'])
        print('beta', beta)


        capm = treasury_yield + beta * (MARKET_RETURN_RATE - treasury_yield)
        print('capm', capm)
        return capm

    def calc_debt_and_equity_weights(self, data, symbol, total_debt):
        market_cap = int(data[symbol]['MARKET_CAPITALIZATION'])
        total = total_debt + market_cap
        return (total_debt / total, market_cap / total)

    def calc_wacc(self, data, symbol, global_data, total_debt):
        tax_rate = self.calc_effective_tax_rate(data, symbol)
        debt_weight, equity_weight = self.calc_debt_and_equity_weights(data, symbol, total_debt)
        print('debt/equity weight', debt_weight, ':', equity_weight)
        equity_cost = self.calc_equity_cost(data, symbol, global_data)
        debt_cost = self.calc_debt_cost_wacc(data, symbol, total_debt)
        print('debt/equity cost', debt_cost, ':', equity_cost)
        wacc = debt_weight * debt_cost * (1 - tax_rate) + equity_weight * equity_cost
        print('wacc', wacc)
        self.signals[symbol]['WACC'] = wacc

    def calc_terminal_value(self, symbol):
        base_value_last_year_estimate = self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'][-1]
        print(self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'])
        print(self.signals[symbol]['WACC'])
        terminal_value = base_value_last_year_estimate * (1 + PERPETUAL_GROWTH_ESTIMATE) / (
                    self.signals[symbol]['WACC'] - PERPETUAL_GROWTH_ESTIMATE)
        if terminal_value < 0:
            self.signals[symbol]['TERMINAL_VALUE'] = 0
        else:
            self.signals[symbol]['TERMINAL_VALUE'] = terminal_value

    def calc_dfc(self, symbol, period_number, data):
        return_multiplier = self.signals[symbol]['WACC'] + 1
        discount_rates = generate_interest_rates(return_multiplier, period_number)
        fcfe_values_to_discount = self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'] + [
            self.signals[symbol]['TERMINAL_VALUE']]
        print('fcfe_values_to_discount', fcfe_values_to_discount)
        discounted_npv_for_cash_flows = [fcfe/dr for dr, fcfe in zip(discount_rates, fcfe_values_to_discount)]
        print('discounted_npv_for_cash_flows', discounted_npv_for_cash_flows)
        dcf = sum(discounted_npv_for_cash_flows)
        print('dcf', dcf)
        market_cap = int(data[symbol]['MARKET_CAPITALIZATION'])
        print('market_cap', market_cap)
        diff = dcf-market_cap
        print(diff, 'diff')
        percentage_diff_dcf_market_cap = (dcf/market_cap - 1)*100
        self.signals[symbol]['DCF'] = round(dcf/1E9, 2)
        self.signals[symbol]['DIFF'] = round(diff/1E9, 2)
        self.signals[symbol]['MARKET_CAP'] = round(market_cap/1E9, 2)
        self.signals[symbol]['PERCENTAGE_DIFF'] = round(percentage_diff_dcf_market_cap, 2)



signal_calculator = CalculateSignal()


@app.route('/')
async def main_page_finance_data():
    symbols = ['IBM', 'AAPL', 'GOOG', 'SSYS', 'DDD', 'HPQ', 'CSCO', 'NTNX', 'CRM']
    function_types = ['CASH_FLOW', 'INCOME_STATEMENT', 'BALANCE_SHEET']
    tasks = []
    for function_type in function_types:
        for symbol in symbols:
            tasks.append(financial_data_aggregator.get_data(function_type, symbol))
            tasks.append(financial_data_aggregator.get_overview_data(symbol))
            tasks.append(financial_data_aggregator.get_price_data(symbol))
            tasks.append(financial_data_aggregator.get_treasury_data())
    await asyncio.gather(*tasks)
    for symbol in symbols:
        signal_calculator.do_calculations(symbol, financial_data_aggregator.financial_data_aggregate,
                                          financial_data_aggregator.global_data)
    return render_template('data.html', data=financial_data_aggregator.financial_data_aggregate,
                           signals=signal_calculator.get_sorted_dict())


if __name__ == '__main__':
    app.run()
