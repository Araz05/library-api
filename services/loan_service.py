"""Loan rules: checkout, return, renew, fines. Knows nothing about HTTP or SQL."""
from datetime import date, timedelta

import notifications
from errors import bad_request, conflict, not_found
from repositories import book_repository, loan_repository, member_repository
from utils import checks, fines, validation

LOAN_PERIOD_DAYS = 14
RENEWAL_PERIOD_DAYS = 14


# ----- calculations on loan rows -----
def current_fine(loan):
    """Fine so far: the stored fine once returned, a growing fine while still open."""
    if loan["returned"] == 0:
        return fines.fine_for(loan["due_date"])
    return loan["fine"]


def amount_owed(loan):
    if loan["returned"] == 0:
        return fines.fine_for(loan["due_date"])
    if loan["fine_paid"] == 0:
        return loan["fine"]
    return 0


def total_owed(loans):
    return sum(amount_owed(loan) for loan in loans)


def count_open_loans(loans):
    return sum(1 for loan in loans if loan["returned"] == 0)


def is_overdue(loan):
    return loan["returned"] == 0 and checks.is_overdue(loan["due_date"])


# ----- use cases -----
def list_loans(only_overdue):
    loans = loan_repository.list_loans()
    if only_overdue:
        loans = [loan for loan in loans if is_overdue(loan)]
    return loans


def get_loan(loan_id):
    loan = loan_repository.get_loan(loan_id)
    if loan is None:
        raise not_found("loan not found")
    return loan


def create_loan(data):
    if not data.get("book_id") or not data.get("member_id"):
        raise bad_request("book_id and member_id are required")
    if data.get("due_date") and not validation.is_valid_date(data["due_date"]):
        raise bad_request("invalid due_date")

    book = book_repository.get_book(data["book_id"])
    if book is None:
        raise not_found("book not found")
    member = member_repository.get_member(data["member_id"])
    if member is None:
        raise not_found("member not found")
    if book["available"] == 0:
        raise conflict("book is not available")

    member_loans = loan_repository.list_loans_for_member(member["id"])
    if checks.has_unpaid_fines(total_owed(member_loans)):
        raise conflict("member has unpaid fines")
    if checks.has_reached_loan_limit(count_open_loans(member_loans), member["type"]):
        raise conflict("loan limit reached")

    today = date.today()
    due_date = data.get("due_date") or (today + timedelta(days=LOAN_PERIOD_DAYS)).isoformat()
    loan = loan_repository.create_loan(book["id"], member["id"], due_date, today.isoformat())
    notifications.notify_checkout(member["email"], book["title"])
    return loan


def return_book(loan_id):
    loan = get_loan(loan_id)
    if loan["returned"] == 1:
        raise conflict("loan already returned")

    fine = fines.fine_for(loan["due_date"])
    updated = loan_repository.mark_returned(loan_id, loan["book_id"], fine)
    member = member_repository.get_member(loan["member_id"])
    book = book_repository.get_book(loan["book_id"])
    notifications.notify_return(member["email"], book["title"], fines.money(fine))
    return updated


def renew_loan(loan_id):
    loan = get_loan(loan_id)
    if loan["returned"] == 1:
        raise conflict("loan already returned")
    if checks.is_overdue(loan["due_date"]):
        raise conflict("overdue loans cannot be renewed")
    if not checks.can_renew_again(loan["renewals"]):
        raise conflict("loan was already renewed")

    new_due = (date.fromisoformat(loan["due_date"]) + timedelta(days=RENEWAL_PERIOD_DAYS)).isoformat()
    updated = loan_repository.extend_loan(loan_id, new_due)
    member = member_repository.get_member(loan["member_id"])
    book = book_repository.get_book(loan["book_id"])
    notifications.notify_renewal(member["email"], book["title"])
    return updated


def pay_fine(loan_id):
    loan = get_loan(loan_id)
    if loan["returned"] == 0:
        raise conflict("return the book before paying")
    if loan["fine"] <= 0 or loan["fine_paid"] == 1:
        raise conflict("no fine to pay")

    updated = loan_repository.mark_fine_paid(loan_id)
    member = member_repository.get_member(loan["member_id"])
    notifications.notify_fine_paid(member["email"], fines.money(loan["fine"]))
    return updated
