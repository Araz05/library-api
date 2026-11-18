"""Report rules. Knows nothing about HTTP or SQL."""
from repositories import book_repository, loan_repository, report_repository
from services import loan_service
from utils import checks, fines


def overdue_report():
    items = []
    total = 0
    for row in report_repository.list_open_loans_with_details():
        if checks.is_overdue(row["due_date"]):
            fine = fines.fine_for(row["due_date"])
            total += fine
            items.append(
                {
                    "loan_id": row["loan_id"],
                    "title": row["title"],
                    "member": row["member"],
                    "days_late": fines.days_late(row["due_date"]),
                    "fine": fines.money(fine),
                }
            )
    return {"items": items, "total_fines": fines.money(total)}


def summary_report():
    loans = loan_repository.list_loans()
    return {
        "total_books": book_repository.count_books(),
        "on_loan": loan_service.count_open_loans(loans),
        "fines_outstanding": fines.money(loan_service.total_owed(loans)),
    }
