import requests


def send_simple_message():
	return requests.post(
		"https://api.mailgun.net/v3/sandbox0ae241d1d72e4e8d9580232d837720fc.mailgun.org/messages",
		auth=("api", "5de17f3e3ec7bc487e5a54100e237cc9-8c8e5529-X"),
		data={"from": "Mailgun Sandbox <postmaster@sandbox0ae241d1d72e4e8d9580232d837720fc.mailgun.org>",
			"to": "antal.tettinger@gmail.com",
			"subject": "Hello Tony Tettinger",
			"text": "Congratulations Tony Tettinger, you just sent an email with Mailgun! You are truly awesome!"})

# You can see a record of this email in your logs: https://app.mailgun.com/app/logs.

# You can send up to 300 emails/day from this sandbox server.
# Next, you should add your own domain so you can send 10000 emails/month for free.
send_simple_message()
