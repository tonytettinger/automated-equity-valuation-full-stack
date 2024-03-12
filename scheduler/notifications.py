import requests

def notify_slack_channel():
    # Define the Slack webhook URL
    webhook_url = "https://hooks.slack.com/services/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"

    # Define the payload data
    payload = {
        "text": "A new signal was generated and is accessible :money_with_wings::\nhttps://tonytettinger.github.io/automated-equity-valuation-full-stack/ "
    }

    # Send the POST request to the Slack webhook URL
    response = requests.post(webhook_url, json=payload)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message:", response.text)