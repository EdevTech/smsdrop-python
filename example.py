import datetime
import logging
import time

import pytz
from dotenv import dotenv_values

from smsdrop import Campaign, Client, Redis

# activate logging
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

config = dotenv_values(".env")

TEST_EMAIL = config.get("TEST_EMAIL")
TEST_PASSWORD = config.get("TEST_PASSWORD")
MY_TIMEZONE = config.get("MY_TIMEZONE")


def main():
    # Initialize the client
    client = Client(email=TEST_EMAIL, password=TEST_PASSWORD, storage=Redis())
    # Get your account profile informations
    print(client.read_me())
    # Get your subscription informations
    print(client.read_subscription())
    # Get your first 500 campaigns
    print(client.read_campaigns(skip=0, limit=500))

    # Send a simple sms
    client.send_sms(message="hi", sender="Max", phone="<phone>")

    # Create a new Campaign
    cp = Campaign(
        title="Test Campaign",
        message="Test campaign content",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
    )
    client.launch_campaign(cp)
    time.sleep(20)  # wait for 20 seconds for the campaign to proceed
    client.refresh_campaign(cp)  # refresh your campaign data
    print(cp.status)  # Output Example : COMPLETED

    # create a scheduled campaign
    dispatch_date = datetime.datetime(2021, 12, 12)
    aware_dispatch_date = pytz.timezone(MY_TIMEZONE).localize(dispatch_date)
    cp2 = Campaign(
        title="Test Campaign 2",
        message="Test campaign content 2",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        defer_until=aware_dispatch_date,
    )
    client.launch_campaign(cp2)
    # You can check for the status at the end of the end ;)

    # create another scheduled campaign using defer_by
    cp2 = Campaign(
        title="Test Campaign 3",
        message="Test campaign content 3",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        defer_by=120,
    )
    client.launch_campaign(cp2)
    time.sleep(120)  # wait for 120 seconds for the campaign to proceed
    client.refresh_campaign(cp)  # refresh your campaign data
    print(cp.status)  # should output : COMPLETED
    # If you get a 'SCHEDULED' printed, you can wait 10 more seconds in case the network
    # is a little slow or the server is a busy


if __name__ == "__main__":
    main()
