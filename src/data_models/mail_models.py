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

    def __str__(self):
        """Providing a human-readable string representation of the mail."""
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H-%M-%S')}"
            f"\nFrom: {self.sender}"
            f"\nTo: {self.recipient}"
            f"\nCC: {self.cc if self.cc else ''}"
            f"\n\nSubject: {self.subject}"
            f"\nBody:"
            f"\n{self.body[:2000]}"
        )
