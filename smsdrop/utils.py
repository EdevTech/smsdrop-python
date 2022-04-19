import json
import logging

from enum import Enum, IntEnum
from httpx import Request, Response


class MessageType(IntEnum):
    PLAIN_TEXT = 0
    FLASH_MESSAGE = 1
    UNICODE = 2


class ShipmentState(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    SCHEDULED = "SCHEDULED"


def log_request(request: Request, /, *, logger: logging.Logger) -> None:
    logger.info(
        f"Request: {request.method} {request.url} - Waiting for response\n"
        f"Content: \n {request.read().decode()}"
    )


def log_response(response: Response, /, *, logger: logging.Logger) -> None:
    request = response.request
    logger.info(
        f"Response: {request.method} {request.url} - Status {response.status_code}\n"
        f"Content : \n {response.read().decode()}"
    )


def get_json_response(response: Response) -> dict:
    try:
        data = response.json()
    except json.decoder.JSONDecodeError:
        data = {}
    return data
