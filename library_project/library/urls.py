# library/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),

    # dashboards
    path("librarian/", views.librarian_dashboard, name="librarian_dashboard"),
    path("reader/", views.reader_dashboard, name="reader_dashboard"),

    # librarian ajax actions
    path("librarian/create-reader/", views.create_reader, name="create_reader"),
    path("librarian/create-loan/", views.create_loan, name="create_loan"),
    path("librarian/return-book/<int:loan_id>/", views.librarian_return_book, name="librarian_return_book"),

    # export
    path("librarian/export/overdue/", views.export_overdue_report, name="export_overdue_report"),
]