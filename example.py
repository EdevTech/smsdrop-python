from dotenv import dotenv_values

from smsdrop import CLient, Campaign

config = dotenv_values(".env")

TEST_EMAIL = config.get("TEST_EMAIL")
TEST_PASSWORD = config.get("TEST_PASSWORD")


def main():
    client = CLient(email=TEST_EMAIL, password=TEST_PASSWORD)
    # client.send_sms(message="hi", sender="Max", phone="22963588213")

    print("------------User-------------")
    print(client.read_me())
    print("--------Subscription---------")
    print(client.read_subscription())
    print("--------Campaigns---------")
    print(client.read_campaigns())
    cp = Campaign(
        title="jagann",
        message="hi there",
        sender="Client",
        recipient_list=["22963588213"],
    )
    client.launch_campaign(cp)
    # cp = client.read_campaign(id="b8fa5494-a1d2-4714-b738-2830e3f5d0fb")
    # print("--before refresh")
    # print(cp.as_dict())
    # import time
    # time.sleep(70)
    # client.refresh_campaign(cp)
    # print("--after refresh")
    # print(cp.as_dict())

    # print(cp.as_dict())


if __name__ == "__main__":
    main()
