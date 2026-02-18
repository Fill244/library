from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Book(models.Model):
    book_code = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    year = models.IntegerField()
    udk = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.title} ({self.book_code})"

class Reader(models.Model):
    reader_id = models.CharField(max_length=50, primary_key=True)
    fio = models.CharField(max_length=255)
    group = models.CharField(max_length=100)

    def __str__(self):
        return self.fio

class Loan(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    issue_date = models.DateField()
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)

    def clean(self):
        # Проверка дат
        if self.issue_date > self.due_date:
            raise ValidationError("issue_date <= due_date")

        if self.return_date:
            if self.due_date > self.return_date:
                raise ValidationError("due_date <= return_date")

        # Проверка одной активной выдачи
        if not self.return_date:
            active = Loan.objects.filter(
                book=self.book,
                return_date__isnull=True
            ).exclude(pk=self.pk)

            if active.exists():
                raise ValidationError("У книги уже есть активная выдача")

    @property
    def is_overdue(self):
        today = timezone.now().date()

        if self.return_date:
            return self.return_date > self.due_date

        return today > self.due_date

    @property
    def days_overdue(self):
        today = timezone.now().date()

        if self.return_date:
            delta = (self.return_date - self.due_date).days
        else:
            delta = (today - self.due_date).days

        return max(delta, 0)

    def __str__(self):
        return f"{self.reader} - {self.book}"
