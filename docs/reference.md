::: smsdrop.Client
    handler: python

::: smsdrop.CampaignCreate
    handler: python

When you create an instance of this class, the only validation that is made is to check if you
set both `defer_by` and `defer_until` which is not allowed. You campaign data is really only validate
when the request is made to the check, so be sure to sanitize your data.

::: smsdrop.Redis
    handler: python

::: smsdrop.User
    handler: python

::: smsdrop.Subscription
    handler: python

::: smsdrop.make_recipient_list
    handler: python

