import requests


def notify_slack_channel(signal_keys):
    tickers = ', '.join(signal_keys)

    # Define the Slack webhook URL
    webhook_url = "https://hooks.slack.com/services/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"

    # Define the payload data
    payload = {
        "text": f"A new signal was generated for the following stocks: {tickers}. Visit \nhttps://tonytettinger.github.io/automated-equity-valuation-full-stack/ or \nhttps://automated-equity-valuation.netlify.app/ "
    }

    # Send the POST request to the Slack webhook URL
    response = requests.post(webhook_url, json=payload)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message:", response.text)
