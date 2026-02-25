# library/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, F
import csv
from datetime import timedelta

from .models import Book, Reader, Loan

# ----- Helpers -----


def home(request):
    # простая главная страница: гостю — кнопка входа, аутентифицированному — редирект на дашборд
    if request.user.is_authenticated:
        if request.user.groups.filter(name="Librarian").exists():
            return redirect("librarian_dashboard")
        return redirect("reader_dashboard")
    return render(request, "home.html")


def login_view(request):
    """Кастомный логин (использует login.html, который вы дали)"""
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.groups.filter(name="Librarian").exists():
                return redirect("librarian_dashboard")
            return redirect("reader_dashboard")
        else:
            error = "Неверный логин или пароль"
    return render(request, "login.html", {"error": error})


@login_required
def logout_view(request):
    logout(request)
    return redirect("home")


def register(request):
    """Регистрация: создаём User, добавляем в группу User и пробуем создать Reader-профиль."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Автодобавление в группу 'User' (если она есть)
            try:
                g = Group.objects.get(name="User")
                user.groups.add(g)
            except Group.DoesNotExist:
                # если группы нет — пропускаем (создайте через admin)
                pass

            # Попытка создать профиль Reader, если модель имеет поле user
            try:
                # попытка создать Reader(user=user, reader_id=username,...)
                Reader.objects.get_or_create(
                    user=user,
                    defaults={"reader_id": user.username, "fio": user.username, "group": ""},
                )
            except Exception:
                # если поле user отсутствует — игнорируем
                pass

            login(request, user)
            return redirect("reader_dashboard")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})


# ---------------- Librarian views ----------------


@login_required
def librarian_dashboard(request):
    # доступ только библиотекарю
    if not request.user.groups.filter(name="Librarian").exists():
        return redirect("home")

    today = timezone.now().date()

    total_books = Book.objects.count()
    active_loans_qs = Loan.objects.filter(return_date__isnull=True)
    active_loans_count = active_loans_qs.count()
    available_books = max(total_books - active_loans_count, 0)

    overdue_qs = active_loans_qs.filter(due_date__lt=today)
    overdue_count = overdue_qs.count()
    overdue_percent = round((overdue_count / active_loans_count * 100), 2) if active_loans_count else 0

    readers = Reader.objects.all()
    books = Book.objects.all()
    active_loans = active_loans_qs.select_related("reader", "book").order_by("due_date")

    default_due_date = (today + timedelta(days=14)).isoformat()

    context = {
        "total_books": total_books,
        "available_books": available_books,
        "active_loans_count": active_loans_count,
        "overdue_count": overdue_count,
        "overdue_percent": overdue_percent,
        "readers": readers,
        "books": books,
        "active_loans": active_loans,
        "overdue_loans": overdue_qs.select_related("reader", "book"),
        "today": today.isoformat(),
        "default_due_date": default_due_date,
        "total_debt": sum(l.days_overdue for l in overdue_qs),
    }
    return render(request, "librarian_dashboard.html", context)


# ---------------- Reader views ----------------


@login_required
def reader_dashboard(request):
    # показать дашборд читателю: свои активные/просроченные/историю
    try:
        # если модель Reader имеет поле user — получаем профиль по user
        reader = Reader.objects.get(user=request.user)
    except Exception:
        # если нет связи — пробуем найти Reader по username == reader_id
        try:
            reader = Reader.objects.get(reader_id=request.user.username)
        except Exception:
            reader = None

    if not reader:
        # если нет привязанного Reader — показываем сообщение/пустые списки
        return render(
            request,
            "reader_dashboard.html",
            {"reader": None, "active_loans": [], "overdue_loans": [], "history_loans": [], "total_debt": 0},
        )

    active_loans = Loan.objects.filter(reader=reader, return_date__isnull=True).select_related("book").order_by("due_date")
    overdue_loans = [l for l in active_loans if l.is_overdue]
    history_loans = Loan.objects.filter(reader=reader, return_date__isnull=False).select_related("book").order_by("-return_date")
    total_debt = sum(l.days_overdue for l in overdue_loans)

    context = {
        "reader": reader,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "history_loans": history_loans,
        "total_debt": total_debt,
    }
    return render(request, "reader_dashboard.html", context)


# ---------------- Actions (AJAX endpoints used by templates) ----------------


@login_required
def create_reader(request):
    if not request.user.groups.filter(name="Librarian").exists():
        return JsonResponse({"success": False, "message": "Нет доступа"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Требуется POST"}, status=400)

    reader_id = request.POST.get("reader_id", "").strip()
    fio = request.POST.get("fio", "").strip()
    group = request.POST.get("group", "").strip()

    if not reader_id or not fio:
        return JsonResponse({"success": False, "message": "Заполните все поля"})

    if Reader.objects.filter(reader_id=reader_id).exists():
        return JsonResponse({"success": False, "message": "Читатель с таким номером уже существует"})

    r = Reader.objects.create(reader_id=reader_id, fio=fio, group=group)
    return JsonResponse({"success": True, "message": "Читатель создан", "reader": {"reader_id": r.reader_id, "fio": r.fio}})


@login_required
def create_loan(request):
    if not request.user.groups.filter(name="Librarian").exists():
        return JsonResponse({"success": False, "message": "Нет доступа"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Требуется POST"}, status=400)

    reader_id = request.POST.get("reader_id")
    book_code = request.POST.get("book_id")
    issue_date = request.POST.get("issue_date")
    due_date = request.POST.get("due_date")

    if not (reader_id and book_code and issue_date and due_date):
        return JsonResponse({"success": False, "message": "Заполните все поля"})

    try:
        reader = Reader.objects.get(reader_id=reader_id)
    except Reader.DoesNotExist:
        return JsonResponse({"success": False, "message": "Читатель не найден"})

    try:
        book = Book.objects.get(book_code=book_code)
    except Book.DoesNotExist:
        return JsonResponse({"success": False, "message": "Книга не найдена"})

    loan = Loan(reader=reader, book=book, issue_date=issue_date, due_date=due_date)
    try:
        loan.full_clean()
        loan.save()
    except ValidationError as e:
        return JsonResponse({"success": False, "message": str(e.message_dict or e.messages)}, status=400)

    return JsonResponse({"success": True, "message": "Выдача успешно оформлена", "loan_id": loan.id})


@login_required
def librarian_return_book(request, loan_id):
    if not request.user.groups.filter(name="Librarian").exists():
        return JsonResponse({"success": False, "message": "Нет доступа"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Требуется POST"}, status=400)

    loan = get_object_or_404(Loan, pk=loan_id)
    if loan.return_date:
        return JsonResponse({"success": False, "message": "Выдача уже закрыта"})

    loan.return_date = timezone.now().date()
    try:
        loan.full_clean()
    except ValidationError as e:
        return JsonResponse({"success": False, "message": str(e.message_dict or e.messages)}, status=400)
    loan.save()
    return JsonResponse({"success": True, "message": "Книга принята"})


@login_required
def export_overdue_report(request):
    if not request.user.groups.filter(name="Librarian").exists():
        return JsonResponse({"success": False, "message": "Нет доступа"}, status=403)

    today = timezone.now().date()
    overdue_qs = Loan.objects.filter(Q(return_date__isnull=True, due_date__lt=today) | Q(return_date__gt=F("due_date"))).select_related(
        "reader", "book"
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="overdue_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["reader_id", "fio", "book_code", "title", "days_overdue"])

    for loan in overdue_qs:
        writer.writerow([loan.reader.reader_id, loan.reader.fio, loan.book.book_code, loan.book.title, loan.days_overdue])

    return response