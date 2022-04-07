# Smsdrop-Python

[![](https://img.shields.io/pypi/v/smsdrop-python.svg)](https://pypi.python.org/pypi/smsdrop-python)
[![python](https://img.shields.io/pypi/pyversions/smsdrop-python)](https://github.com/EdevTech/smsdrop-python)
[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/EdevTech/smsdrop-python/blob/master/LICENSE)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


- Documentation: <a href="https://tobi-de.github.io/smsdrop-python/" target="_blank">https://tobi-de.github.io/smsdrop-python/</a>
- Source Code: <a href="https://github.com/Tobi-De/smsdrop-python/" target="_blank">https://github.com/Tobi-De/smsdrop-python/</a>

The official python sdk for the [smsdrop](https://smsdrop.net) api.

## Quickstart

```python
import datetime
import logging
import time

import pytz
from dotenv import dotenv_values

from smsdrop import Campaign, Client, RedisStorage

# Enable Debug Logging
# This will og the API request and response data to the console:
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

config = dotenv_values(".env")

TEST_EMAIL = config.get("TEST_EMAIL")
TEST_PASSWORD = config.get("TEST_PASSWORD")
MY_TIMEZONE = config.get("MY_TIMEZONE")


def main():
    # Initialize the client
    client = Client(
        email=TEST_EMAIL, password=TEST_PASSWORD, storage=RedisStorage()
    )
    # Get your account profile information
    print(client.get_profile())
    # Get your subscription information's
    print(client.get_subscription())
    # Get your first 500 campaigns
    print(client.get_campaigns(skip=0, limit=500))

    # Send a simple sms
    client.send_message(message="hi", sender="Max", phone="<phone>")

    # Create a new Campaign
    cp = Campaign(
        title="Test Campaign",
        message="Test campaign content",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
    )
    client.launch(cp)
    time.sleep(20)  # wait for 20 seconds for the campaign to proceed
    client.refresh(cp)  # refresh your campaign data
    print(cp.status)  # Output Example : COMPLETED

    # create a scheduled campaign
    naive_dispatch_date = datetime.datetime.now() + datetime.timedelta(hours=1)
    aware_dispatch_date = pytz.timezone(MY_TIMEZONE).localize(
        naive_dispatch_date
    )
    cp2 = Campaign(
        title="Test Campaign 2",
        message="Test campaign content 2",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        # The date will automatically be sent in iso format with the timezone data
        defer_until=aware_dispatch_date,
    )
    client.launch(cp2)
    # If you check the status one hour from now it should return 'COMPLETED'

    # create another scheduled campaign using defer_by
    cp3 = Campaign(
        title="Test Campaign 3",
        message="Test campaign content 3",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        defer_by=120,
    )
    client.launch(cp3)
    time.sleep(120)  # wait for 120 seconds for the campaign to proceed
    client.refresh(cp3)  # refresh your campaign data
    print(cp3.status)  # should output : COMPLETED
    # If you get a 'SCHEDULED' printed, you can wait 10 more seconds in case the network
    # is a little slow or the server is busy


if __name__ == "__main__":
    main()
```
