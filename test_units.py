"""Unit tests for the new modules. test_api.py is untouched.

The first group needs no HTTP and no database. The last group uses a
MockNotifier so we can check emails without reading outbox.txt.
"""
import os
import tempfile
import unittest
from datetime import date, timedelta

import notifications
from db import init_db
from errors import LibraryError, api_error, error_response
from notifications import MockNotifier
from services import loan_service
from utils import checks, fines, validation


def days_from_today(days):
    return (date.today() + timedelta(days=days)).isoformat()


class FineTests(unittest.TestCase):
    def test_late_fine_is_fifty_cents_per_day(self):
        self.assertEqual(fines.fine_for(days_from_today(-4)), 2.0)

    def test_no_fine_when_on_time_or_early(self):
        self.assertEqual(fines.fine_for(days_from_today(0)), 0)
        self.assertEqual(fines.fine_for(days_from_today(5)), 0)

    def test_money_rounds_to_cents(self):
        self.assertEqual(fines.money(2.499999), 2.5)


class ValidationTests(unittest.TestCase):
    def test_email(self):
        self.assertTrue(validation.is_valid_email("a@b.com"))
        self.assertFalse(validation.is_valid_email("nope"))
        self.assertFalse(validation.is_valid_email(None))

    def test_isbn(self):
        self.assertTrue(validation.is_valid_isbn("978-0441013593"))
        self.assertFalse(validation.is_valid_isbn("123"))
        self.assertFalse(validation.is_valid_isbn(None))

    def test_date(self):
        self.assertTrue(validation.is_valid_date("2026-01-15"))
        self.assertFalse(validation.is_valid_date("next week"))

    def test_member_type(self):
        self.assertTrue(validation.is_valid_member_type("staff"))
        self.assertFalse(validation.is_valid_member_type("alien"))


class CheckTests(unittest.TestCase):
    def test_loan_limits(self):
        self.assertTrue(checks.has_reached_loan_limit(3, "student"))
        self.assertFalse(checks.has_reached_loan_limit(3, "staff"))
        self.assertTrue(checks.has_reached_loan_limit(5, "staff"))

    def test_overdue(self):
        self.assertTrue(checks.is_overdue(days_from_today(-1)))
        self.assertFalse(checks.is_overdue(days_from_today(0)))

    def test_unpaid_fines_and_renewals(self):
        self.assertTrue(checks.has_unpaid_fines(0.5))
        self.assertFalse(checks.has_unpaid_fines(0))
        self.assertTrue(checks.can_renew_again(0))
        self.assertFalse(checks.can_renew_again(1))


class ErrorTests(unittest.TestCase):
    def test_api_error_carries_message_and_status(self):
        error = api_error("custom message", 418)
        self.assertIsInstance(error, LibraryError)
        self.assertEqual((error.message, error.status_code), ("custom message", 418))

    def test_error_response_builds_json(self):
        from flask import Flask

        with Flask(__name__).app_context():
            response, status = error_response("book not found", 404)
            self.assertEqual(status, 404)
            self.assertEqual(response.get_json(), {"error": "book not found"})


class MockNotifierTests(unittest.TestCase):
    def setUp(self):
        self.original_dir = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        init_db()
        self.mock = MockNotifier()
        notifications.set_notifier(self.mock)

    def tearDown(self):
        notifications.set_notifier(notifications.FileOutboxNotifier())
        os.chdir(self.original_dir)
        self.temp_dir.cleanup()

    def test_checkout_notifies_member_without_writing_a_file(self):
        loan_service.create_loan({"book_id": 1, "member_id": 1})
        self.assertTrue(self.mock.was_sent(email="sam@campus.edu", subject="Book checked out"))
        self.assertFalse(os.path.exists("outbox.txt"))

    def test_return_notification_includes_fine(self):
        loan_service.return_book(1)
        self.assertEqual(self.mock.sent[0]["body"], "You returned Code Complete. Fine: $2.5")

    def test_failed_checkout_sends_nothing(self):
        with self.assertRaises(LibraryError):
            loan_service.create_loan({"book_id": 5, "member_id": 1})
        self.assertEqual(self.mock.sent, [])


if __name__ == "__main__":
    unittest.main()
