"""Tests for the GroupMe notification module."""

from collections import defaultdict
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch

import httpx

from data_models.ai_models import EmailCategorization, MsgTier
from notifications.gm_notify import (
    build_summary,
    gm_notify,
    summarize_and_post,
    GM_HEADERS,
    GM_URL,
)


class BuildSummaryTests(TestCase):
    """Tests for the build_summary function."""

    def setUp(self):
        self._template = "S:{s_tier}\nA:{a_tier}\nB:{b_count}\nC:{c_count}"
        self._template_path = Path("test_template.txt")
        self._open_mock = mock_open(read_data=self._template)

        # A basic EmailCategorization to reuse across tests
        self._categorization = MagicMock(spec=EmailCategorization)
        self._categorization.email.sender = "TEST_SENDER"
        self._categorization.email.subject = "TEST_SUBJECT"
        self._categorization.result.reasoning = "TEST_REASONING"

    def _make_msg_data(self, **tier_overrides):
        """Build a msg_data dict with empty tiers, overridden by kwargs."""
        data = defaultdict(list)
        for tier, items in tier_overrides.items():
            data[tier] = items
        return data

    # --- Template formatting ---

    def test_build_summary_formats_template(self):
        """build_summary should return a string using the provided template."""
        input_dict = {
            # Many:
            MsgTier.TIER_1_SOVEREIGN: [self._categorization, self._categorization],
            # One
            MsgTier.TIER_2_HIGH_SIGNAL: [self._categorization],
            # Others are missing
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)
        self.assertIsInstance(resp, str)
        self.assertTrue(resp.endswith("B:0\nC:0"))

    def test_build_summary_all_empty_tiers(self):
        """All tiers empty should still produce a valid formatted string."""
        input_dict = {}
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        self.assertIsInstance(resp, str)

    # --- Tier chunk content ---

    def test_build_summary_t1_includes_sender_subject_reasoning(self):
        """Tier 1 chunk should include sender, subject, and reasoning for each mail."""
        input_dict = {
            MsgTier.TIER_1_SOVEREIGN: [self._categorization],
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        s_tier_chunk = (
            "S:Tier 1: Sovereign:"
            "\nMsgs: 1"
            "\n\nSender: TEST_SENDER"
            "\nSubject: TEST_SUBJECT"
            "\nReason: TEST_REASONING"
        )
        self.assertIn(s_tier_chunk, resp)

    def test_build_summary_t2_includes_sender_subject_reasoning(self):
        """Tier 2 chunk should include sender, subject, and reasoning for each mail."""
        input_dict = {
            MsgTier.TIER_2_HIGH_SIGNAL: [self._categorization],
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        a_tier_chunk = (
            "A:Tier 2: High Signal:"
            "\nMsgs: 1"
            "\n\nSender: TEST_SENDER"
            "\nSubject: TEST_SUBJECT"
            "\nReason: TEST_REASONING"
        )

        self.assertIn(a_tier_chunk, resp)

    def test_build_summary_t3_reflected_as_count_only(self):
        """Tier 3 should appear as a count, not individual message details."""
        input_dict = {
            MsgTier.TIER_3_GENERAL: [self._categorization],
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        b_tier_chunk = "B:1"
        self.assertIn(b_tier_chunk, resp)

    def test_build_summary_t4_reflected_as_count_only(self):
        """Tier 4 should appear as a count, not individual message details."""
        input_dict = {
            MsgTier.TIER_4_NOISE: [self._categorization],
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        c_tier_chunk = "C:1"
        self.assertIn(c_tier_chunk, resp)

    def test_build_summary_multiple_msgs_in_tier(self):
        """Multiple messages in a tier should all appear in the output chunk."""
        input_dict = {
            MsgTier.TIER_1_SOVEREIGN: [self._categorization, self._categorization],
        }
        with patch("builtins.open", self._open_mock):
            resp = build_summary(input_dict, self._template_path)

        msg_chunk = (
            "\n\nSender: TEST_SENDER\nSubject: TEST_SUBJECT\nReason: TEST_REASONING"
        )
        s_tier_chunk = ("S:Tier 1: Sovereign:\nMsgs: 2") + msg_chunk + msg_chunk
        self.assertIn(s_tier_chunk, resp)


class GmNotifyTests(TestCase):
    """Tests for the gm_notify and _post_to_chat functions."""

    def setUp(self):
        self._bot_id = "TEST_BOT_ID"
        self._msg = "TEST_MESSAGE"

    # --- Happy path ---

    def test_gm_notify_posts_correct_payload(self):
        """gm_notify should POST with the correct bot_id and text."""
        with patch("httpx.post") as p:
            gm_notify(self._bot_id, self._msg)
            p.assert_called_once_with(
                GM_URL,
                json={"bot_id": self._bot_id, "text": self._msg},
                headers=GM_HEADERS,
            )

    def test_gm_notify_succeeds_on_200(self):
        """A 200 response should complete without raising."""
        response = httpx.Response(
            status_code=200, request=MagicMock(spec=httpx.Request, url=GM_URL)
        )
        with patch("httpx.post", return_value=response):
            gm_notify(self._bot_id, self._msg)

        # Simply assert that it doesn't raise an exception.

    # --- Error handling ---

    def test_gm_notify_raises_on_4xx(self):
        """A 4xx HTTP response should raise an HTTPStatusError."""
        response = httpx.Response(
            status_code=401, request=MagicMock(spec=httpx.Request, url=GM_URL)
        )
        with (
            patch("httpx.post", return_value=response),
            self.assertRaises(httpx.HTTPStatusError),
        ):
            gm_notify(self._bot_id, self._msg)

    def test_gm_notify_raises_on_5xx(self):
        """A 5xx HTTP response should raise an HTTPStatusError."""
        response = httpx.Response(
            status_code=500, request=MagicMock(spec=httpx.Request, url=GM_URL)
        )
        with (
            patch("httpx.post", return_value=response),
            self.assertRaises(httpx.HTTPStatusError),
        ):
            gm_notify(self._bot_id, self._msg)

    def test_gm_notify_retries_on_transport_error(self):
        """A TransportError should trigger a retry up to 3 times."""
        response = httpx.Response(
            status_code=200, request=MagicMock(spec=httpx.Request, url=GM_URL)
        )
        with patch(
            "httpx.post", side_effect=[httpx.TransportError("Ahh"), response]
        ) as p:
            gm_notify(self._bot_id, self._msg)
            self.assertEqual(p.call_count, 2)

    def test_gm_notify_reraises_after_max_retries(self):
        """After exhausting retries on TransportError, the exception should propagate."""
        with (
            patch("httpx.post", side_effect=httpx.TransportError("Ahh")),
            self.assertRaises(httpx.TransportError),
        ):
            gm_notify(self._bot_id, self._msg)


class SummarizeAndPostTests(TestCase):
    """Tests for the summarize_and_post orchestration function."""

    def setUp(self):
        self._bot_id = "TEST_BOT_ID"
        self._template_path = Path("test_template.txt")
        self._categorization = MagicMock(spec=EmailCategorization)
        self._categorization.email.sender = "TEST_SENDER"
        self._categorization.email.subject = "TEST_SUBJECT"
        self._categorization.result.reasoning = "TEST_REASONING"

    def test_summarize_and_post_calls_build_summary_and_gm_notify(self):
        """summarize_and_post should delegate to build_summary and gm_notify."""
        bs_mock = MagicMock(return_value="Message String!")
        gm_notify_mock = MagicMock()
        data = {MsgTier.TIER_1_SOVEREIGN: [self._categorization]}
        with patch.multiple(
            "notifications.gm_notify", build_summary=bs_mock, gm_notify=gm_notify_mock
        ):
            summarize_and_post(data, self._template_path, self._bot_id)
            bs_mock.assert_called_once_with(data, self._template_path)
            gm_notify_mock.assert_called_once()

    def test_summarize_and_post_passes_summary_to_gm_notify(self):
        """The output of build_summary should be what gets passed to gm_notify."""
        bs_mock = MagicMock(return_value="Message String!")
        gm_notify_mock = MagicMock()
        data = {MsgTier.TIER_1_SOVEREIGN: [self._categorization]}
        with patch.multiple(
            "notifications.gm_notify", build_summary=bs_mock, gm_notify=gm_notify_mock
        ):
            summarize_and_post(data, self._template_path, self._bot_id)
            gm_notify_mock.assert_called_once_with(self._bot_id, bs_mock.return_value)
