import requests
import schedule
import time

TIME_ZONE = 'America/New_York'
AFTER_MARKET_CLOSING_TIME = '16:01'


def request_local_endpoint():
    endpoint = 'http://127.0.0.1:5000/check_stocks?scheduler=true'
    try:
        print('scheduled task starting...')
        requests.get(endpoint)
    except Exception as e:
        print(f"Error occurred while requesting local endpoint: {e}")


schedule.every().minute.do(request_local_endpoint)

while True:
    schedule.run_pending()
    time.sleep(1)
