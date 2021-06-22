import datetime
import logging
import time

import pytz
from dotenv import dotenv_values

from smsdrop import CampaignCreate, Client, RedisStorage

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
    # Get your account profile informations
    print(client.read_me())
    # Get your subscription informations
    print(client.read_subscription())
    # Get your first 500 campaigns
    print(client.read_campaigns(skip=0, limit=500))

    # Send a simple sms
    client.send_message(message="hi", sender="Max", phone="<phone>")

    # Create a new Campaign
    cp = CampaignCreate(
        title="Test Campaign",
        message="Test campaign content",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
    )
    cp = client.launch_campaign(cp)
    time.sleep(20)  # wait for 20 seconds for the campaign to proceed
    cp = client.read_campaign(cp.id)  # refresh your campaign data
    print(cp.status)  # Output Example : COMPLETED

    # create a scheduled campaign
    naive_dispatch_date = datetime.datetime.now() + datetime.timedelta(hours=1)
    aware_dispatch_date = pytz.timezone(MY_TIMEZONE).localize(
        naive_dispatch_date
    )
    cp2 = CampaignCreate(
        title="Test Campaign 2",
        message="Test campaign content 2",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        # The date will automatically be send in isoformat with the timezone data
        defer_until=aware_dispatch_date,
    )
    cp2 = client.launch_campaign(cp2)
    # If you check the status one hour from now it should return 'COMPLETED'

    # create another scheduled campaign using defer_by
    cp3 = CampaignCreate(
        title="Test Campaign 3",
        message="Test campaign content 3",
        sender="TestUser",
        recipient_list=["<phone1>", "<phone2>", "<phone3>"],
        defer_by=120,
    )
    cp3 = client.launch_campaign(cp3)
    time.sleep(120)  # wait for 120 seconds for the campaign to proceed
    cp3 = client.read_campaign(cp3.id)  # refresh your campaign data
    print(cp3.status)  # should output : COMPLETED
    # If you get a 'SCHEDULED' printed, you can wait 10 more seconds in case the network
    # is a little slow or the server is busy


if __name__ == "__main__":
    main()
