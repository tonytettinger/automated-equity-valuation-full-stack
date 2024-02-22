import schedule
import time

from notifications import notify

TIME_ZONE = 'America/New_York'
AFTER_MARKET_CLOSING_TIME = '16:01'

def job():
    print("I'm working...")

schedule.every().minute.do(notify)


while True:
    schedule.run_pending()
    time.sleep(1)