"""GMail Parser logic for fetching e-mails and returning a list."""

import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable

import ezgmail

from data_models.mail_models import MailMessage

LINKEDIN_MAILER_FROM = "inmail-hit-reply"
class MailParserBase(ABC):
    """Baseclass for Mail parsers.

    This class acts as an interface definition for mail parsers. This interface makes
    for potential ease of expansion to other email clients.
    """
    @abstractmethod
    def parse_mail(self, oldest_datetime: dt.datetime) -> list[MailMessage]:
        """Parse MailMessages from the mail service."""
        ...

# If we go to a bunch of different classes, we should move this into a dedicated file.
class GMailParser(MailParserBase):
    """Gmail implementation of MailParser"""
    UNREAD_LABEL="UNREAD"
    def __init__(self):
        ezgmail.init()
        self._email_user: str = ezgmail.EMAIL_ADDRESS

    def parse_mail(self, oldest_datetime: dt.date) -> list[MailMessage]:
        """Parse the inbox and return a list of MailMessages for processing."""
        raw_threads = self._fetch_unread_threads(oldest_datetime)
        result = list(self._thread_to_mail_msg(raw_threads, mark_as_read=True))
        return result

    @staticmethod
    def _fetch_unread_threads(oldest_datetime: dt.date) -> list[ezgmail.GmailThread]:
        search_query = GMailParser._build_search_query(
            LINKEDIN_MAILER_FROM, oldest_datetime
        )
        return ezgmail.search(search_query)

    @staticmethod
    def _build_search_query(
        sender: str | None = None,
        oldest_date: dt.date | None = None
    ) -> str:
        query_components: list[str] = [f"label:{GMailParser.UNREAD_LABEL}"]
        # Append the sender query:
        if sender:
            query_components.append(f"from:{sender}")
        # Append the date query:
        if oldest_date:
            query_components.append(f"after:{oldest_date.strftime('%Y-%m-%d')}")
        # collect all the variables we used and join together with a space
        return " ".join(query_components)

    @staticmethod
    def _thread_to_mail_msg(
        gmail_threads: Iterable[ezgmail.GmailThread],
        mark_as_read: bool = False
    ) -> Generator[MailMessage]:
        for thread in gmail_threads:
            top_msg = thread.messages[0]
            yield MailMessage(
                sender=top_msg.sender,
                recipient=[top_msg.recipient],
                cc=None,
                subject=top_msg.subject,
                body=top_msg.body,
                timestamp=top_msg.timestamp
            )
            if mark_as_read:
                top_msg.markAsRead()
