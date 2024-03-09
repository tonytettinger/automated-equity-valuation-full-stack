import os
from collections import defaultdict, OrderedDict
from operator import getitem

import requests

from sql.helpers import database_access

# Percentage of market return rate estimate
MARKET_RETURN_RATE = database_access.get_market_rate()

# Perpetual growth estimate
PERPETUAL_GROWTH_ESTIMATE = database_access.get_perpetual_growth()

SAFETY_MARGIN = database_access.get_safety_margin()


def safe_division(x, y, default=0):
    try:
        result = x / y
    except ZeroDivisionError:
        result = default
    return result


# Return percentage differences, if the value would be negative we just take the maximum value
def calculate_percentage_difference(array):
    percentage_differences = []
    for i in range(len(array) - 1):
        current_element = array[i]
        next_element = array[i + 1]
        percentage_difference = (safe_division((next_element - current_element), current_element))
        percentage_differences.append(percentage_difference)
    print('percentage_differences:', percentage_differences)
    average = safe_division(sum(percentage_differences), len(percentage_differences))
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
    print('rates', rates)
    return rates


class CalculateSignal:
    def __init__(self):
        self.sortedSignals = {}
        self.signals = defaultdict(lambda: defaultdict(dict))
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    def get_signal(self):
        return self.signals

    def get_sorted_dict(self):
        return self.sortedSignals['MARKET_CAP']

    def add_sorted_dict_by_category(self, category):
        self.sortedSignals[category] = OrderedDict(
            sorted(self.signals.items(), key=lambda x: getitem(x[1], 'MARKET_CAP')))

    async def do_calculations(self, symbol, data, global_data):
        total_net_income_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['netIncome']))
        total_revenue_periods = list(map(int, data[symbol]['INCOME_STATEMENT']['totalRevenue']))
        period_number = len(total_net_income_periods)
        total_debt = int(data[symbol]['BALANCE_SHEET']['shortTermDebt'][0]) + int(
            data[symbol]['BALANCE_SHEET']['longTermDebt'][0])

        try:
            self.calc_fcfe_net_income_ratio(symbol, data, total_net_income_periods)
            self.calc_net_income_margin(symbol, total_net_income_periods, total_revenue_periods)
            self.calc_earnings_growth(symbol, total_revenue_periods)
            self.calc_projected_free_cash_flow(symbol, total_revenue_periods, 4)
            self.calc_wacc(data, symbol, global_data, total_debt)
            self.calc_terminal_value(symbol)
            await self.calc_dfc(symbol, period_number, data)
            self.add_sorted_dict_by_category('MARKET_CAP')
        except Exception as e:
            print('Exception occurred during signal calculations: ' + str(e), 'for symbol:', symbol)
            return

    # Calculate the average Free Cash Flow to Equity / Net Income ratio for the time period
    def calc_fcfe_net_income_ratio(self, symbol, data, total_net_income_periods):
        print("Calculating FCFE net income")
        total_cash_flow_periods = list(map(int, data[symbol]['CASH_FLOW']['operatingCashflow']))
        capex_periods = list(map(int, data[symbol]['CASH_FLOW']['capitalExpenditures']))

        fcfe_net_income_ratio = [safe_division((total_cash_flow - capex), total_net_income) for
                                 total_cash_flow, capex, total_net_income in
                                 zip(total_cash_flow_periods, capex_periods, total_net_income_periods)]

        self.signals[symbol]['FCFE_NET_INCOME_RATIO'] = sum(fcfe_net_income_ratio) / len(fcfe_net_income_ratio)

    # Calculate the net income margin and take the minimum for the most conservative estimate
    def calc_net_income_margin(self, symbol, total_net_income_periods, total_revenue_periods):

        net_income_margin = [safe_division(total_net_income_period, total_revenue_period) for
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

    def calc_debt_cost_wacc(self, data, symbol, total_debt):
        interest_expense = data[symbol]['INCOME_STATEMENT']['interestExpense'][0]
        return safe_division(float(interest_expense), float(total_debt))

    def calc_equity_cost(self, data, symbol, global_data):
        treasury_yield = float(global_data['TREASURY_YIELD']) * 0.01
        print('treasury yield:', treasury_yield)
        beta = float(data[symbol]['BETA'])
        print('beta', beta)

        capm = treasury_yield + beta * (MARKET_RETURN_RATE - treasury_yield)
        print('capm', capm)
        return capm

    def calc_debt_and_equity_weights(self, data, symbol, total_debt):
        print('data', data[symbol])
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
        terminal_value = base_value_last_year_estimate * (1 + PERPETUAL_GROWTH_ESTIMATE) / (
                self.signals[symbol]['WACC'] - PERPETUAL_GROWTH_ESTIMATE)
        if terminal_value < 0:
            self.signals[symbol]['TERMINAL_VALUE'] = 0
        else:
            self.signals[symbol]['TERMINAL_VALUE'] = terminal_value

    async def calc_dfc(self, symbol, period_number, data):
        return_multiplier = self.signals[symbol]['WACC'] + 1
        discount_rates = generate_interest_rates(return_multiplier, period_number)
        fcfe_values_to_discount = self.signals[symbol]['PROJECTED_FREE_CASH_FLOWS'] + [
            self.signals[symbol]['TERMINAL_VALUE']]
        print('fcfe_values_to_discount', fcfe_values_to_discount)
        discounted_npv_for_cash_flows = [fcfe / dr for dr, fcfe in zip(discount_rates, fcfe_values_to_discount)]
        print('discounted_npv_for_cash_flows', discounted_npv_for_cash_flows)
        dcf = sum(discounted_npv_for_cash_flows)
        print('dcf', dcf, symbol)
        market_cap = int(data[symbol]['MARKET_CAPITALIZATION'])
        print('market_cap', market_cap)
        diff = dcf - market_cap
        print(diff, 'difference is')
        percentage_diff_dcf_market_cap = dcf / market_cap - 1
        self.signals[symbol]['DCF'] = round(dcf / 1E9, 2)
        self.signals[symbol]['DCF_PRICE_PER_SHARE'] = round(dcf / float(data[symbol]['SHARES_OUTSTANDING']), 2)
        self.signals[symbol]['DIFF'] = round(diff / 1E9, 2)
        self.signals[symbol]['MARKET_CAP'] = round(market_cap / 1E9, 2)
        self.signals[symbol]['PERCENTAGE_DIFF'] = round(percentage_diff_dcf_market_cap * 100, 2)
        is_over_safety_margin = percentage_diff_dcf_market_cap > SAFETY_MARGIN
        if not is_over_safety_margin:
            del self.signals[symbol]
        else:
            await self.get_MACD(symbol)
            self.signals[symbol]['LATEST_PRICE'] = data[symbol]['LATEST_PRICE']
            await self.get_news(symbol)

    async def get_MACD(self, symbol):
        api_url = f'https://www.alphavantage.co/query?function=MACD&symbol={symbol}&interval=daily&series_type=open&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            print('macd data is', data, symbol)
            if len(data) == 0:
                self.signals[symbol]['MACD'] = {}
            else:
                self.signals[symbol]['MACD'] = data["Technical Analysis: MACD"]
        else:
            self.signals[symbol]['MACD'] = {}

    async def get_news(self, symbol):
        api_url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={self.api_key}'
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            print('news data for', symbol, 'is ', data)
            if len(data) == 0:
                self.signals[symbol]['NEWS'] = {}
                self.signals[symbol]['SENTIMENT_AVG'] = {}
            else:
                news_feed = data["feed"]
                news_feed_to_add = []
                symbol_sentiment = []
                for news in news_feed:
                    try:
                        for ticker_sentiment in news["ticker_sentiment"]:
                            current_symbol = ticker_sentiment["ticker"]
                            if current_symbol == symbol:
                                symbol_sentiment.append(float(ticker_sentiment["ticker_sentiment_score"]))
                                print('ticker sentiment', ticker_sentiment)
                                if float(ticker_sentiment["relevance_score"]) >= 0.25:
                                    news_feed_to_add.append(news)
                    except:
                        print('error in getting news sentiment')
                        continue
                sentiment_average = round(sum(symbol_sentiment)/len(symbol_sentiment), 2)

                self.signals[symbol]['NEWS'] = news_feed_to_add
                self.signals[symbol]['SENTIMENT_AVG'] = sentiment_average
                print('news feed to add', news_feed_to_add)
        else:
            self.signals[symbol]['NEWS'] = {}
            self.signals[symbol]['SENTIMENT_AVG'] = {}
