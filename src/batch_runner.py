"""Class for executing the main batch of the program."""
# I get an ick if there is any logic in the main besides parsing command line args.

import datetime as dt

from loguru import logger
from pprint import pprint

from ai_interop.ai_submision import MailCategorizer
from data_models.config_models import AppConfig
from mail_parsing.parsers import GMailParser, MailParserBase


class TrixieJob:
    """Class that represents a single "TrixieJob" instance."""

    def __init__(self, cfg: AppConfig, dry_run: bool = False):
        """Initializes a TrixieJob"""
        self._mail_parser: MailParserBase = GMailParser(dry_run=dry_run)
        self._categorizer = MailCategorizer(
            cfg.ai_model, cfg.api_key, cfg.sys_prompt_path
        )
        self._oldest_date = dt.datetime.now() - dt.timedelta(days=7)

    async def run_job(self):
        """Executes the TrixieJob."""
        # Step 1: Fetch appropriate e-mails from the inbox
        logger.info("Parsing E-Mails...")
        mails = self._mail_parser.parse_mail(self._oldest_date)
        # Step 2: Send them off to the AI agent for categorization.
        logger.info("{} E-Mails found. Categorizing...", len(mails))
        categorized_results = await self._categorizer.categorize_mails(mails)
        # Step 3: Notify of results
        for cat in categorized_results.values():
            for m, c in cat:
                pprint((c.tier, c.reasoning, m.sender))
        #   NOTE: Step 3 will likely evolve to "store results" and the notification will
        #   run as a separate batch for summaries etc.
