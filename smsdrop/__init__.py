"""Main module of the smsdrop sdk
"""
from .exceptions import (
    BadCredentialsError,
    InsufficientSmsError,
    ServerError,
    ValidationError,
)
from .models import Campaign, MessageType, ShipmentState, Subscription, User
from .smsdrop import Client
from .storages import BaseStorage, Dummy, Redis, SimpleDict
from .utils import make_recipient_list

__author__ = """Tobi DEGNON"""
__email__ = "degnonfrancis@gmail.com"
__version__ = "0.1.0"
