from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import LoanForm, ReturnForm, RegisterForm
import csv
from django.contrib.auth import login
from django.contrib.auth.models import Group
from .models import *


@login_required
def overdue_report(request):
    if request.user.groups.filter(name="User").exists():
        loans = Loan.objects.filter(reader__user=request.user)
    else:
        loans = Loan.objects.all()

    # --- ФИЛЬТРЫ ---
    issue_from = request.GET.get("issue_from")
    issue_to = request.GET.get("issue_to")
    reader_id = request.GET.get("reader")
    book_code = request.GET.get("book")
    overdue_from = request.GET.get("overdue_from")
    overdue_to = request.GET.get("overdue_to")
    

    if issue_from:
        loans = loans.filter(issue_date__gte=issue_from)
    if issue_to:
        loans = loans.filter(issue_date__lte=issue_to)
    if reader_id:
        loans = loans.filter(reader__reader_id=reader_id)
    if book_code:
        loans = loans.filter(book__book_code=book_code)
    overdue_loans = []

    for loan in loans:
        if loan.is_overdue:
            days = loan.days_overdue
            if overdue_from:
                if days < int(overdue_from):
                    continue
            if overdue_to:
                if days > int(overdue_to):
                    continue
            overdue_loans.append(loan)

    total_loans = Loan.objects.count()
    total_active = Loan.objects.filter(return_date__isnull=True).count()
    total_returned = Loan.objects.filter(return_date__isnull=False).count()

    total_overdue = len(overdue_loans)

    percent = 0
    if total_active > 0:
        percent = round((total_overdue / total_active) * 100, 2)

    context = {
        "loans": overdue_loans,
        "percent": percent,
        "total_loans": total_loans,
        "total_active": total_active,
        "total_returned": total_returned,
        "total_overdue": total_overdue,
        "readers": Reader.objects.all(),
        "books": Book.objects.all(),
    }

    return render(request, "overdue_report.html", context)

def export_overdue_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="overdue.csv"'

    writer = csv.writer(response)
    writer.writerow(['reader_id', 'book_code', 'days_overdue'])

    for loan in Loan.objects.all():
        if loan.is_overdue:
            writer.writerow([
                loan.reader.reader_id,
                loan.book.book_code,
                loan.days_overdue
            ])

    return response

@login_required
def create_loan(request):
    if not request.user.groups.filter(name="Librarian").exists():
        return redirect("overdue_report")
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('overdue_report')
    else:
        form = LoanForm()

    return render(request, 'create_loan.html', {'form': form})

@login_required
def return_book(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if not request.user.groups.filter(name="Librarian").exists():
        return redirect("overdue_report")
    if request.method == 'POST':
        form = ReturnForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            return redirect('overdue_report')
    else:
        form = ReturnForm(instance=loan)

    return render(request, 'return_book.html', {'form': form, 'loan': loan})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Добавляем в группу User
            group = Group.objects.get(name="User")
            user.groups.add(group)

            login(request, user)
            return redirect("overdue_report")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})

def home(request):
    return render(request, "home.html")