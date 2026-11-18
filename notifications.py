"""Notifications.

Services call `send_email(...)` or one of the `notify_*` helpers and never know
HOW the message is delivered. The delivery is a swappable "notifier":

  * FileOutboxNotifier - the default. It appends to outbox.txt, which stands in
    for a real mail server (the API tests read this file).
  * MockNotifier       - a mock object (https://en.wikipedia.org/wiki/Mock_object).
    It sends nothing; it records every message in memory so a test can check
    "was an email sent, to whom, with what subject?" without touching any file.
"""

OUTBOX_PATH = "outbox.txt"


class Notifier:
    def send_email(self, email, subject, body):
        raise NotImplementedError


class FileOutboxNotifier(Notifier):
    def send_email(self, email, subject, body):
        with open(OUTBOX_PATH, "a") as f:
            f.write("TO: " + email + " | SUBJECT: " + subject + " | BODY: " + body + "\n")


class MockNotifier(Notifier):
    def __init__(self):
        self.sent = []

    def send_email(self, email, subject, body):
        self.sent.append({"email": email, "subject": subject, "body": body})

    def was_sent(self, email=None, subject=None):
        return any(
            (email is None or m["email"] == email) and (subject is None or m["subject"] == subject)
            for m in self.sent
        )


_notifier = FileOutboxNotifier()


def get_notifier():
    return _notifier


def set_notifier(notifier):
    """Swap the delivery mechanism (e.g. to a MockNotifier in tests)."""
    global _notifier
    _notifier = notifier


def send_email(email, subject, body):
    _notifier.send_email(email, subject, body)


# One function per message, so wording lives here and nowhere else.
def notify_checkout(email, title):
    send_email(email, "Book checked out", "You checked out " + title)


def notify_renewal(email, title):
    send_email(email, "Loan renewed", "You renewed " + title)


def notify_return(email, title, fine):
    send_email(email, "Book returned", "You returned " + title + ". Fine: $" + str(fine))


def notify_fine_paid(email, amount):
    send_email(email, "Fine paid", "We received $" + str(amount))
