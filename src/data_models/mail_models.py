"""File for defining the generic Mail-related objects."""

import datetime as dt
from typing import NamedTuple


class MailMessage(NamedTuple):
    """Simple model representing a single Mail message."""

    sender: str
    recipient: list[str]
    cc: list[str] | None
    subject: str
    body: str
    timestamp: dt.datetime
