import requests
from bs4 import BeautifulSoup

URL = "https://finance.yahoo.com/u/yahoo-finance/watchlists/tech-stocks-that-move-the-market/"
headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
page = requests.get(URL,headers=headers)
soup = BeautifulSoup(page.content, "html.parser")
tickers_container = soup.findAll('a', attrs={'data-test': 'symbol-link'})
tickers = [ticker.get_text() for ticker in tickers_container]

print('tickers', tickers)