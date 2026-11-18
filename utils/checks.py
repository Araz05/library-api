"""Library rule checks: small pure functions that answer yes/no questions.

They take plain values (no database rows, no HTTP), so they are easy to test.
"""
from utils import fines

STUDENT_LOAN_LIMIT = 3
STAFF_LOAN_LIMIT = 5
MAX_RENEWALS = 1


def is_overdue(due_date):
    return fines.days_late(due_date) > 0


def loan_limit_for(member_type):
    return STAFF_LOAN_LIMIT if member_type == "staff" else STUDENT_LOAN_LIMIT


def has_reached_loan_limit(open_loans, member_type):
    return open_loans >= loan_limit_for(member_type)


def has_unpaid_fines(amount_owed):
    return amount_owed > 0


def can_renew_again(renewals):
    return renewals < MAX_RENEWALS
