"""Module for managing the submission to the AI Agents"""

import asyncio
import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import tenacity
from httpx import TransportError
from loguru import logger
from openrouter import OpenRouter

from data_models.ai_models import AIResponse, EmailCategorization, MsgTier
from data_models.mail_models import MailMessage


class MailCategorizationError(Exception): ...


class MailCategorizer:
    """Class for wrapping requests to OpenRouter and returning the resultant mail."""

    MSG_TEMPLATE = """
        Please return the following email content and categorize it.

        <email>
        {email_body}
        </email>
    """

    def __init__(self, ai_model: str, api_key: str, system_prompt_path: Path):
        """Initialize the class."""
        self._ai_model = ai_model
        self._router = OpenRouter(api_key=api_key)
        with open(system_prompt_path) as f:
            self._sys_prompt = f.read()

    async def categorize_mails(
        self, mail_list: Iterable[MailMessage]
    ) -> dict[MsgTier, list[EmailCategorization]]:
        """Submit some MailMessages to the agent and return categorized results."""
        tasks = (self._categorize_mail(m) for m in mail_list)
        resps = await asyncio.gather(*tasks)

        result_dict: dict[MsgTier, list[EmailCategorization]] = defaultdict(list)
        for r in resps:
            result_dict[r.result.tier].append(r)

        return result_dict

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(TransportError),
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(min=1, max=4, multiplier=1),
        before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    async def _categorize_mail(self, m: MailMessage) -> EmailCategorization:
        response = await self._router.chat.send_async(
            model=self._ai_model,
            messages=[
                {"role": "system", "content": self._sys_prompt},
                {
                    "role": "user",
                    "content": self.MSG_TEMPLATE.format(email_body=str(m)),
                },
            ],
            response_format={"type": "json_object"},
        )
        msg_content = response.choices[0].message.content
        if msg_content is None:
            raise MailCategorizationError("AI response came back null")
        pattern = r"(?:`{3}json\s*)?([\s\S]*?)(?:\s*`{3})?$"
        re_match = re.match(pattern, str(msg_content))
        if re_match is None:
            raise MailCategorizationError("No regex match found. Check the pattern.")

        raw_json = re_match.group(1)
        return EmailCategorization(
            email=m, result=AIResponse.model_validate_json(raw_json)
        )
