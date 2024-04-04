from ratelimit import limits, sleep_and_retry

# 30 calls per minute
CALLS = 30
RATE_LIMIT_SECONDS = 60


@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT_SECONDS)
def check_limit():
    ''' Empty function just to check for calls to API '''
    return
