from django.urls import path
from .views import (
    overdue_report,
    export_overdue_csv,
    create_loan,
    return_book
)

urlpatterns = [
    path("overdue/", overdue_report, name="overdue_report"),
    path("overdue/export/", export_overdue_csv, name="export_overdue"),
    path("loan/create/", create_loan, name="create_loan"),
    path("loan/return/<int:loan_id>/", return_book, name="return_book"),
]
