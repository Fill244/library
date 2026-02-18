from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from .forms import LoanForm, ReturnForm
import csv
from .models import Loan


def overdue_report(request):
    today = timezone.now().date()

    loans = Loan.objects.all()

    overdue_loans = []

    for loan in loans:
        if loan.is_overdue:
            overdue_loans.append(loan)

    total_active = Loan.objects.filter(return_date__isnull=True).count()
    total_overdue = len(overdue_loans)

    percent = 0
    if total_active > 0:
        percent = round((total_overdue / total_active) * 100, 2)

    context = {
        "loans": overdue_loans,
        "percent": percent
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

def create_loan(request):
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('overdue_report')
    else:
        form = LoanForm()

    return render(request, 'create_loan.html', {'form': form})

def return_book(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == 'POST':
        form = ReturnForm(request.POST, instance=loan)
        if form.is_valid():
            form.save()
            return redirect('overdue_report')
    else:
        form = ReturnForm(instance=loan)

    return render(request, 'return_book.html', {'form': form, 'loan': loan})
