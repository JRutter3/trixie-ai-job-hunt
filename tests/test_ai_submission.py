"""Tests for the MailCategorizer AI submission module."""

from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from httpx import TransportError
from openrouter.components import ChatAssistantMessage, ChatChoice, ChatResult

from ai_interop.ai_submision import MailCategorizationError, MailCategorizer
from data_models.ai_models import MsgTier
from data_models.mail_models import MailMessage


class MailCategorizerTests(IsolatedAsyncioTestCase):
    """Tests for the MailCategorizer class."""

    def setUp(self):
        """Set up shared test fixtures."""
        self._api_key = "TEST_API_KEY"
        self._ai_model = "TEST_MODEL"
        self._sys_prompt = "You are a helpful assistant."
        self._system_prompt_path = Path("test_prompt.txt")

        open_mock = mock_open(read_data=self._sys_prompt)
        with patch("builtins.open", open_mock):
            self._categorizer = MailCategorizer(
                ai_model=self._ai_model,
                api_key=self._api_key,
                system_prompt_path=self._system_prompt_path,
            )

        # A basic MailMessage to reuse across tests
        self._mail = MagicMock(spec=MailMessage)

    def _make_chat_response_mock(self, content: str | None) -> MagicMock:
        raw_result = MagicMock(
            spec=ChatResult,
            choices=[
                MagicMock(
                    spec=ChatChoice,
                    message=MagicMock(spec=ChatAssistantMessage, content=content),
                )
            ],
        )
        return raw_result

    # --- categorize_mails ---

    async def test_categorize_mails_returns_grouped_by_tier(self):
        """Results from categorize_mails should be grouped by MsgTier."""
        result_str = (
            '{"tier": "tier_1_sovereign", "score": 25'
            ',"summary": "Mail from Bill Gates. He wants to give you money"'
            ',"reasoning":"its free money","action_required":"true"}'
        )
        response_mock = self._make_chat_response_mock(result_str)
        router_mock = MagicMock(
            chat=MagicMock(send_async=AsyncMock(return_value=response_mock))
        )
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch:
            resp = await self._categorizer.categorize_mails([self._mail])

        for k in resp:
            self.assertIsInstance(k, MsgTier)

    async def test_categorize_mails_multiple_tiers(self):
        """Mails of different tiers should land in their respective tier buckets."""
        result_strs = [
            (
                '{"tier": "tier_1_sovereign", "score": 75'
                ',"summary": "Mail from Bill Gates. He wants to give you money"'
                ',"reasoning":"its free money","action_required":"true"}'
            ),
            (
                '{"tier": "tier_2_high_signal", "score": 15'
                ',"summary": "Mail from Bill Gates. He wants to give you money"'
                ',"reasoning":"its free money","action_required":"true"}'
            ),
            (
                '{"tier": "tier_4_noise", "score": 15'
                ',"summary": "Mail from Bill Gates. He wants to give you money"'
                ',"reasoning":"its free money","action_required":"true"}'
            ),
        ]
        response_mocks = [self._make_chat_response_mock(x) for x in result_strs]
        router_mock = MagicMock(
            chat=MagicMock(send_async=AsyncMock(side_effect=response_mocks))
        )
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch:
            resp = await self._categorizer.categorize_mails([self._mail] * 3)

        for tier in [
            MsgTier.TIER_1_SOVEREIGN,
            MsgTier.TIER_2_HIGH_SIGNAL,
            MsgTier.TIER_4_NOISE,
        ]:
            self.assertIn(tier, resp)

        self.assertNotIn(MsgTier.TIER_3_GENERAL, resp)

    async def test_categorize_mails_empty_input(self):
        """An empty mail list should return an empty dict without error."""
        resp = await self._categorizer.categorize_mails({})
        self.assertFalse(resp)

    # --- _categorize_mail ---

    async def test_categorize_mail_null_response_raises(self):
        """
        A null message content in the AI response should raise MailCategorizationError.
        """
        response = self._make_chat_response_mock(None)
        router_mock = MagicMock(
            chat=MagicMock(send_async=AsyncMock(return_value=response))
        )
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch as _, self.assertRaisesRegex(MailCategorizationError, "null"):
            await self._categorizer.categorize_mails([self._mail])

    async def test_categorize_mail_handles_markdown_fenced_json(self):
        """A response wrapped in ```json ... ``` fences should still parse correctly."""
        result_str = (
            '```json{"tier": "tier_1_sovereign", "score": 25'
            ',"summary": "Mail from Bill Gates. He wants to give you money"'
            ',"reasoning":"its free money","action_required":"true"}```'
        )
        response = self._make_chat_response_mock(result_str)
        router_mock = MagicMock(
            chat=MagicMock(send_async=AsyncMock(return_value=response))
        )
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch:
            resp = await self._categorizer.categorize_mails([self._mail])

        # Assert that the length is 1, though success is anything that does not throw
        self.assertEqual(len(resp), 1)

    async def test_categorize_mail_retries_on_transport_error(self):
        """A TransportError should trigger a retry up to 3 times before reraising."""
        result_str = (
            '{"tier": "tier_1_sovereign", "score": 25'
            ',"summary": "Mail from Bill Gates. He wants to give you money"'
            ',"reasoning":"its free money","action_required":"true"}'
        )
        response = self._make_chat_response_mock(result_str)
        async_send_mock = AsyncMock(side_effect=[TransportError("Ahh!"), response])

        router_mock = MagicMock(chat=MagicMock(send_async=async_send_mock))
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch:
            await self._categorizer.categorize_mails([self._mail])

        # Assert that we retried when we got the TransportError
        self.assertEqual(async_send_mock.await_count, 2)

    async def test_categorize_mail_reraises_after_max_retries(self):
        """
        After exhausting retries on TransportError, the exception should propagate.
        """
        async_send_mock = AsyncMock(side_effect=TransportError("Ahh!"))

        router_mock = MagicMock(chat=MagicMock(send_async=async_send_mock))
        router_patch = patch.object(self._categorizer, "_router", router_mock)
        with router_patch as _, self.assertRaisesRegex(TransportError, "Ahh!") as _:
            await self._categorizer.categorize_mails([self._mail])

        # We tried three times, then re-raised
        self.assertEqual(async_send_mock.await_count, 3)
