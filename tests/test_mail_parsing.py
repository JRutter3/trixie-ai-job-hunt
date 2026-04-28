"""Tests that our email parser works correctly and handles error cases etc."""

import datetime as dt
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ezgmail import GmailMessage, GmailThread

from mail_parsing.parsers import GMailParser


class GMailParserTests(TestCase):
    """Module for testing GMail parsing tests."""

    def setUp(self):
        """Set up the test."""
        self._email_token = "TEST_TOKEN"  # noqa: S105 This is obviously not a real pwd
        self._email_creds = "TEST_CREDS"
        self._last_datetime = dt.datetime(2017, 11, 30)
        self._parser = GMailParser(self._email_token, self._email_creds)

        ezgmail_init_mock = MagicMock()
        self._ezgmail_patch = patch("ezgmail.init", ezgmail_init_mock)
        self._ezgmail_patch.start()

    def tearDown(self):
        """Clean-up any persistent patches etc."""
        self._ezgmail_patch.stop()

    def test_parse_mail_maps_fields(self):
        """Test that parse_mail executes correctly given normal circumstances."""
        msg_body = "Hi <candidate>,\nI have an exciting opportunity for you!"
        mail_msg = MagicMock(
            spec=GmailMessage,
            sender="TEST_SENDER",
            recipient="MY_EMAIL",
            subject="TEST_SUBJECT",
            body=msg_body,
            timestamp=dt.datetime(2017, 12, 3, 14, 0, 0),
        )
        mailsearch_mock = MagicMock(
            return_value=[MagicMock(spec=GmailThread, messages=[mail_msg])]
        )

        with patch("ezgmail.search", mailsearch_mock):
            msgs = self._parser.parse_mail(self._last_datetime)

        # Assert that the each field gets pulled from the gmail response and returned.
        msg = msgs[0]
        self.assertEqual(msg.subject, "TEST_SUBJECT")
        self.assertListEqual(msg.recipient, ["MY_EMAIL"])
        self.assertEqual(msg.body, msg_body)
        self.assertIsNone(msg.cc)
        self.assertEqual(msg.sender, "TEST_SENDER")
        self.assertEqual(msg.timestamp, dt.datetime(2017, 12, 3, 14, 0, 0))

    def test_parse_mail_returns_multiples(self):
        """Test that parse_mail executes correctly given normal circumstances."""
        msg_body = "Hi <candidate>,\nI have an exciting opportunity for you!"
        mail_msg = MagicMock(
            spec=GmailMessage,
            sender="TEST_SENDER",
            recipient="MY_EMAIL",
            subject="TEST_SUBJECT",
            body=msg_body,
            timestamp=dt.datetime(2017, 12, 3, 14, 0, 0),
        )
        mailsearch_mock = MagicMock(
            return_value=[MagicMock(spec=GmailThread, messages=[mail_msg])] * 3
        )

        with patch("ezgmail.search", mailsearch_mock):
            msgs = self._parser.parse_mail(self._last_datetime)

        # Assert that the each field gets pulled from the gmail response and returned.
        self.assertEqual(len(msgs), 3)

    def test_parse_mail_no_results(self):
        """Test the pase_mail function if the search comes back with no results."""
        mailsearch_mock = MagicMock(return_value=[])
        with patch("ezgmail.search", mailsearch_mock):
            msgs = self._parser.parse_mail(self._last_datetime)
            self.assertListEqual(msgs, [])

    def test__build_search_query_all_args(self):
        """Test the private _build_search_query function."""
        oldest_date = dt.date(2019, 8, 22)
        sender_filter = "bill.braskey"
        result = self._parser._build_search_query(sender_filter, oldest_date)
        expected_result = "label:UNREAD from:bill.braskey after:2019-08-22"
        self.assertEqual(result, expected_result)

    def test__build_search_query_no_args(self):
        """Test the _build_search_query function with NO args passed."""
        result = self._parser._build_search_query()
        expected_result = "label:UNREAD"
        self.assertEqual(result, expected_result)

    def test__build_search_query_sender_only(self):
        """Test the _build_saerch_query function with only the sender passed."""
        result = self._parser._build_search_query("bill.braskey")
        expected_result = "label:UNREAD from:bill.braskey"
        self.assertEqual(result, expected_result)

    def test__build_search_query_date_only(self):
        """Test the _build_search_query function with only the oldest date passed."""
        result = self._parser._build_search_query(oldest_date=dt.date(2014, 8, 23))
        expected_result = "label:UNREAD after:2014-08-23"
        self.assertEqual(result, expected_result)
