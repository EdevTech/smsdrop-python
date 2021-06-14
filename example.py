import time

from dotenv import dotenv_values

from smsdrop import Client, Campaign

config = dotenv_values(".env")

TEST_EMAIL = config.get("TEST_EMAIL")
TEST_PASSWORD = config.get("TEST_PASSWORD")


def main():
    # Initialize the client
    client = Client(email=TEST_EMAIL, password=TEST_PASSWORD)
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


if __name__ == "__main__":
    main()
