import json
from functools import wraps

import httpx
from httpx import Response


def get_json_response(response: Response) -> dict:
    default = {"responsecode": None}
    try:
        json_content = response.json()
    except json.decoder.JSONDecodeError:
        return default
    else:
        json_content = (
            json_content if json_content and isinstance(json_content, dict) else default
        )
        return json_content


def log_request_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            response = func(self, *args, **kwargs)
        except httpx.RequestError as e:
            self.logger.error(f"An error occurred while requesting {e.request.url}")
            exit(-1)
        else:
            return response

    return wrapper
