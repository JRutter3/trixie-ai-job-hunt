"""Module for curating and sending messages to the GroupME room."""

import logging
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path

import httpx
import tenacity
from loguru import logger

from data_models.ai_models import EmailCategorization, MsgTier

GM_URL = "https://api.groupme.com/v3/bots/post"
GM_HEADERS = {"Content-Type": "application/json"}

TIER_LABEL_MAP = {
    MsgTier.TIER_1_SOVEREIGN: "Tier 1: Sovereign",
    MsgTier.TIER_2_HIGH_SIGNAL: "Tier 2: High Signal",
    MsgTier.TIER_3_GENERAL: "Tier 3: General Interest",
    MsgTier.TIER_4_NOISE: "Tier 4: Noise",
}


def summarize_and_post(
    msg_data: Mapping[MsgTier, Collection[EmailCategorization]],
    summary_template_path: Path,
    bot_id: str,
) -> None:
    msg = build_summary(msg_data, summary_template_path)
    gm_notify(bot_id, msg)


def build_summary(
    msg_data: Mapping[MsgTier, Collection[EmailCategorization]],
    summary_template_path: Path,
) -> str:
    """Take the dict of tier/email info and builds a message to send to notifiers."""
    with open(summary_template_path) as f:
        summary_template = f.read()

    t1_chunk = f"{TIER_LABEL_MAP[MsgTier.TIER_1_SOVEREIGN]}:\n" + _build_tier_component(
        msg_data[MsgTier.TIER_1_SOVEREIGN]
    )
    t2_chunk = (
        f"{TIER_LABEL_MAP[MsgTier.TIER_2_HIGH_SIGNAL]}:\n"
        + _build_tier_component(msg_data[MsgTier.TIER_2_HIGH_SIGNAL])
    )
    t3_count = len(msg_data[MsgTier.TIER_3_GENERAL])
    t4_count = len(msg_data[MsgTier.TIER_4_NOISE])

    return summary_template.format(
        s_tier=t1_chunk, a_tier=t2_chunk, b_count=t3_count, c_count=t4_count
    )


def _build_tier_component(category_iter: Iterable[EmailCategorization]) -> str:
    msg_len = 0
    result = ""
    for msg in category_iter:
        msg_len += 1
        chunk = (
            f"Sender: {msg.email.sender}"
            f"\nSubject: {msg.email.subject}"
            f"\nReason: {msg.result.reasoning}"
        )
        result += f"\n\n{chunk}"

    return f"Msgs: {msg_len}" + result


def gm_notify(bot_id: str, msg: str) -> None:
    post_data = {
        "bot_id": bot_id,
        "text": msg,
    }
    web_response = _post_to_chat(post_data)
    try:
        web_response.raise_for_status()
    except httpx.HTTPStatusError:
        logger.error(
            "Posting to GroupMe returned an error: {code} | {reason} | {text}",
            code=web_response.status_code,
            reason=web_response.reason_phrase,
            text=web_response.text,
        )
        raise


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(httpx.TransportError),
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(min=1, max=4, multiplier=1),
    before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
    reraise=True,
)
def _post_to_chat(post_data: Mapping[str, str]) -> httpx.Response:
    return httpx.post(GM_URL, json=post_data, headers=GM_HEADERS)
