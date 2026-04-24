"""GMail Parser logic for fetching e-mails and returning a list."""

import datetime as dt
import os
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Protocol

from loguru import logger

from data_models.mail_models import MailMessage

# ezgmail attempts to initialize before we ask it to. It will complain that there is no
# credentials / token file (because there isn't yet). Only import it HERE if we are
# type-checking.  When running at runtime, we will import it as part of
# GMailParser._initialize_ezgmail

LINKEDIN_MAILER_FROM = "inmail-hit-reply"
CREDS_LOCATION = Path()

if TYPE_CHECKING:
    from ezgmail import GmailThread

    class EZGmailInterface(Protocol):
        """Quick interface for us to appropriately hint the EZGmail library"""

        def search(self, query: str) -> list[GmailThread]: ...
        def init(
            self,
            userId: ... = ...,
            tokenFile: ... = ...,
            credentialsFile: ... = ...,
        ) -> bool: ...


@contextmanager
def temp_working_dir(new_working_dir: os.PathLike[str]) -> Generator[None]:
    """Context manager for temporarily changing the working directory"""
    origin = os.getcwd()
    os.chdir(new_working_dir)
    try:
        yield
    finally:
        os.chdir(origin)


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

    UNREAD_LABEL = "UNREAD"

    def __init__(
        self,
        token_str: str,
        creds_str: str,
        dry_run: bool = False,
    ):
        self._token = token_str
        self._creds = creds_str
        self._dry_run = dry_run
        self._ezgmail: EZGmailInterface | None = None

    @property
    def ezgmail(self) -> "EZGmailInterface":
        if self._ezgmail is None:
            raise RuntimeError(
                "GMailParser._initialize_ezgmail must be called"
                " before accessing GMailParser.ezgmail."
            )
        return self._ezgmail

    def parse_mail(self, oldest_datetime: dt.date) -> list[MailMessage]:
        """Parse the inbox and return a list of MailMessages for processing."""

        self._initialize_ezgmail()
        logger.debug("Reading unread mails")
        raw_threads = self._fetch_unread_threads(oldest_datetime)

        result = list(
            self._thread_to_mail_msg(raw_threads, mark_as_read=not self._dry_run)
        )
        return result

    def _initialize_ezgmail(self) -> None:
        logger.debug("Initializing GMail credentials")

        # This hack-around makes ezgmail work. We could consider using the raw
        # google-api-pyth0on-client instead, but this works and has some nice sugar.
        with TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            with temp_working_dir(dir_path):
                creds_path = dir_path / Path("credentials.json")
                token_path = dir_path / Path("token.json")
                with open(creds_path, "w") as f:
                    f.write(self._creds)
                with open(token_path, "w") as f:
                    f.write(self._token)

                import ezgmail  # when at Runtime, import this thing HERE

                ezgmail.init()

        self._ezgmail = ezgmail

    def _fetch_unread_threads(self, oldest_datetime: dt.date) -> list["GmailThread"]:
        search_query = GMailParser._build_search_query(
            LINKEDIN_MAILER_FROM, oldest_datetime
        )
        return self.ezgmail.search(search_query)

    @staticmethod
    def _build_search_query(
        sender: str | None = None, oldest_date: dt.date | None = None
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
        gmail_threads: Iterable["GmailThread"], mark_as_read: bool = False
    ) -> Generator[MailMessage]:
        for thread in gmail_threads:
            top_msg = thread.messages[0]
            yield MailMessage(
                sender=top_msg.sender,
                recipient=[top_msg.recipient],
                cc=None,
                subject=top_msg.subject,
                body=top_msg.body,
                timestamp=top_msg.timestamp,
            )
            if mark_as_read:
                top_msg.markAsRead()
