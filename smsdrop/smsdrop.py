import datetime
import logging
from dataclasses import dataclass
from typing import Optional, List

import httpx
from httpx import codes

from .constants import (
    BASE_URL,
    LOGIN_PATH,
    USER_PATH,
    SUBSCRIPTION_PATH,
    CAMPAIGN_BASE_PATH,
    CAMPAIGN_RETRY_PATH,
)
from .exceptions import (
    ServerError,
    BadCredentialsError,
    InsufficientSmsError,
    ValidationError,
)
from .models import Campaign, User, Subscription, MessageType, campaign_public_fields

logger = logging.getLogger(__name__)


@dataclass
class Client:
    email: str
    password: str
    _bearer_token: Optional[str] = None

    def _login(self):
        response = httpx.post(
            url=BASE_URL + LOGIN_PATH,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"username": self.email, "password": self.password},
        )
        if response.status_code == codes.OK:
            self._bearer_token = response.json()["access_token"]
        elif response.status_code == codes.BAD_REQUEST:
            raise BadCredentialsError("Your credentials are incorrect")
        elif codes.is_server_error(response.status_code):
            raise ServerError("The server is failing, try later")
        else:
            logger.info(response.text)

    def _token_has_expired(self) -> bool:
        try:
            response = httpx.get(
                url=BASE_URL + USER_PATH,
                headers={"Authorization": f"Bearer {self._bearer_token}"},
            )
        except httpx.RequestError as e:
            logger.error(e)
        else:
            return response.status_code == codes.UNAUTHORIZED

    @property
    def _http_client(self) -> httpx.Client:
        # refresh token if needed
        if self._token_has_expired():
            self._login()
        return httpx.Client(
            base_url=BASE_URL, headers={"Authorization": f"Bearer {self._bearer_token}"}
        )

    def _send_request(
            self, path: str, payload: Optional[dict] = None
    ) -> httpx.Response:
        try:
            response = (
                self._http_client.post(
                    url=path, json=payload, headers={"content-type": "application/json"}
                )
                if payload
                else self._http_client.get(url=path)
            )
        except httpx.RequestError as e:
            logger.error(e)
        else:
            if codes.is_server_error(response.status_code):
                raise ServerError("The server is failing, try later")
            if response.status_code == codes.UNPROCESSABLE_ENTITY:
                raise ValidationError(errors=response.json()["detail"])
            return response

    def send_sms(
            self,
            message: str,
            sender: str,
            phone: str,
            dispatch_date: Optional[datetime.datetime] = None,
    ):
        payload = {
            "message": message,
            "message_type": MessageType.PLAIN_TEXT,
            "sender": sender,
            "recipient_list": [phone],
        }
        if dispatch_date:
            payload["dispatch_date"] = dispatch_date
        response = self._send_request(path=CAMPAIGN_BASE_PATH, payload=payload)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        return Campaign.from_response(response.json())

    def launch_campaign(self, campaign: Campaign):
        payload = campaign.as_dict(only=campaign_public_fields)
        response = self._send_request(path=CAMPAIGN_BASE_PATH, payload=payload)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )
        campaign.update(data=response.json())

    def refresh_campaign(self, campaign: Campaign):
        assert (
            Campaign.id
        ), "You can't refresh data for a campaign that hasn't yet been launched"
        refreshed_cp = self.read_campaign(id=campaign.id)
        campaign.update(refreshed_cp.as_dict())

    def retry_campaign(self, id: str):
        payload = {"id": id}
        response = self._send_request(path=CAMPAIGN_RETRY_PATH, payload=payload)
        if response.status_code == codes.CREATED:
            raise InsufficientSmsError(
                "Insufficient sms credits to launch this campaign"
            )

    def read_campaign(self, id: str) -> Campaign:
        request_path = CAMPAIGN_BASE_PATH + f"/{id}"
        response = self._send_request(path=request_path)
        return Campaign.from_response(response.json())

    def read_campaigns(self, skip: int = 0, limit: int = 100) -> List[Campaign]:
        request_path = CAMPAIGN_BASE_PATH + f"/?skip={skip}&limit={limit}"
        response = self._send_request(path=request_path)
        camaigns = [Campaign.from_response(cp) for cp in response.json()]
        return camaigns

    def read_subscription(self) -> Subscription:
        response = self._send_request(path=SUBSCRIPTION_PATH)
        data = response.json()
        return Subscription(id=data["id"], nbr_sms=data["nbr_sms"])

    def read_me(self) -> User:
        response = self._send_request(path=USER_PATH)
        data = response.json()
        return User(email=data["email"], id=data["id"], is_active=data["is_active"])
