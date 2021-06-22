class BadCredentialsError(Exception):
    pass


class ServerError(Exception):
    """Occurs when the qos server is busy or fails for some reason"""


class InsufficientSmsError(Exception):
    def __init__(self, id, *args):
        self.id = id
        super().__init__(*args)


class ValidationError(Exception):
    # When the api send back a 422 error
    def __init__(self, errors: list):
        def formatted_msg(error: dict):
            loc = error["loc"]
            source = loc[1]
            extra = loc[2:]
            detail = error["msg"]
            return (
                f"{source}{extra}: {detail}"
                if extra
                else f"{source}: {detail}"
            )

        msg = "\n".join([formatted_msg(error) for error in errors])
        super().__init__(msg)


class BadTokenError(Exception):
    pass
