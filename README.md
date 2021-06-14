# Smsdrop-Python

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/tterb/atomic-design-ui/blob/master/LICENSEs)
[![](https://img.shields.io/pypi/v/smsdrop-python.svg)](https://pypi.python.org/pypi/smsdrop-python)

* Documentation: https://qosic-sdk.readthedocs.io.

The official python sdk for the [smdrop](https://smsdrop.net) api.

## Usage/Examples

```python
from smsdrop import CLient, Campaign

config = dotenv_values(".env")

TEST_EMAIL = config.get("TEST_EMAIL")
TEST_PASSWORD = config.get("TEST_PASSWORD")


def main():
    # Initialize the client
    client = CLient(email=TEST_EMAIL, password=TEST_PASSWORD)
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

```

  
