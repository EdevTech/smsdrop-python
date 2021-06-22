import json
import logging
from functools import wraps

import httpx
from httpx import Request, Response

from .models import MessageType


def log_request(request: Request, logger: logging.Logger):
    json_content = (
        json.loads(request.content) if request.method == "POST" else {}
    )
    logger.debug(
        f"Request: {request.method} {request.url} - Waiting for response\n"
        f"Content: \n {json.dumps(json_content, indent=2, sort_keys=True)}"
    )


def log_response(response: Response, logger: logging.Logger):
    request = response.request
    logger.debug(
        f"Response: {request.method} {request.url} - Status {response.status_code}\n"
        f"Content : \n {json.dumps(response.json(), indent=2, sort_keys=True)}"
    )


def sanitize_payload(payload: dict):
    payload = {key: value for key, value in payload.items() if value}
    return payload


def cast_message_type(content: dict) -> dict:
    if "message_type" in content:
        content["message_type"] = MessageType(content["message_type"])
    return content


def get_json_response(response: Response) -> dict:
    default = {"responsecode": None}
    try:
        json_content = response.json()
    except json.decoder.JSONDecodeError:
        return default
    else:
        json_content = (
            json_content
            if json_content and isinstance(json_content, dict)
            else default
        )
        return json_content


def log_request_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            response = func(self, *args, **kwargs)
        except httpx.RequestError as e:
            self.logger.error(
                f"An error occurred while requesting {e.request.url}"
            )
            exit(-1)
        else:
            return response

    return wrapper
