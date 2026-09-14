from django.db import models
from django.contrib.auth.models import User

class GradeClass(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Sinf nomi")  # masalan: 9-A, 10-B
    class_teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_classes', verbose_name="Sinf rahbari")

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Fan nomi")
    code = models.CharField(max_length=20, blank=True, verbose_name="Fan kodi")
    icon = models.CharField(max_length=50, default="📚", verbose_name="Icon/Emoji")
    color = models.CharField(max_length=20, default="#3B82F6", verbose_name="Rang (HEX)")

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile', null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers', verbose_name="Bosh fani")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqami")

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.subject})"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    grade_class = models.ForeignKey(GradeClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Sinf")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon raqami")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Ota-onasining telefoni")
    telegram_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telegram Chat ID")

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.grade_class or 'Sinfsiz'})"


class Timetable(models.Model):
    DAYS = [
        (1, 'Dushanba'),
        (2, 'Seshanba'),
        (3, 'Chorshanba'),
        (4, 'Payshanba'),
        (5, 'Juma'),
        (6, 'Shanba'),
    ]
    grade_class = models.ForeignKey(GradeClass, on_delete=models.CASCADE, related_name='timetables', verbose_name="Sinf")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="O'qituvchi")
    day_of_week = models.IntegerField(choices=DAYS, verbose_name="Hafta kuni")
    time_slot = models.CharField(max_length=50, verbose_name="Vaqti (masalan, 08:30 - 09:15)")
    room = models.CharField(max_length=50, blank=True, verbose_name="Xona")

    class Meta:
        verbose_name = "Dars Jadvali"
        verbose_name_plural = "Dars Jadvallari"
        ordering = ['day_of_week', 'time_slot']

    def __str__(self):
        return f"{self.grade_class} — {self.get_day_of_week_display()} — {self.subject}"


class Grade(models.Model):
    GRADE_TYPES = [
        ('KUNDALIK', 'Kundalik dars'),
        ('NAZORAT', 'Nazorat ishi'),
        ('CHORAK', 'Choraklik baho'),
        ('HOMEWORK', 'Uyga vazifa'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades', verbose_name="O'quvchi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades', verbose_name="Fan")
    score = models.IntegerField(verbose_name="Baho (1-5 yoki 1-100)")
    grade_type = models.CharField(max_length=20, choices=GRADE_TYPES, default='KUNDALIK', verbose_name="Baho turi")
    date = models.DateField(verbose_name="Sana")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Baho"
        verbose_name_plural = "Baholar"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.score} ({self.date})"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('B', 'Bor'),
        ('K', 'Kech qoldi'),
        ('Y', "Yo'q (Sababsiz)"),
        ('S', "Sababli yo'q"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances', verbose_name="O'quvchi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances', verbose_name="Fan")
    date = models.DateField(verbose_name="Sana")
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='B', verbose_name="Holat")
    notified_telegram = models.BooleanField(default=False, verbose_name="Telegramga yuborildi")

    class Meta:
        unique_together = ('student', 'subject', 'date')
        verbose_name = "Yo'qlama"
        verbose_name_plural = "Yo'qlamalar"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} — {self.subject} — {self.date} — {self.status}"


class Homework(models.Model):
    grade_class = models.ForeignKey(GradeClass, on_delete=models.CASCADE, related_name='homeworks', verbose_name="Sinf")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Vazifa topshirig'i")
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(verbose_name="Topshirish muddati")

    class Meta:
        verbose_name = "Uyga vazifa"
        verbose_name_plural = "Uyga vazifalar"
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.grade_class} — {self.subject}: {self.title}"


# Bilim.uz Test Platformasi Modellari
class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name="Test nomi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes', verbose_name="Fan")
    grade_level = models.IntegerField(default=9, verbose_name="Sinf darajasi")
    time_limit_minutes = models.IntegerField(default=15, verbose_name="Vaqt chegari (daqiqa)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    def __str__(self):
        return f"{self.title} ({self.subject})"


class Question(models.Model):
    OPTION_CHOICES = [
        ('A', 'A Variant'),
        ('B', 'B Variant'),
        ('C', 'C Variant'),
        ('D', 'D Variant'),
    ]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', verbose_name="Test")
    text = models.TextField(verbose_name="Savol matni")
    option_a = models.CharField(max_length=255, verbose_name="A variant")
    option_b = models.CharField(max_length=255, verbose_name="B variant")
    option_c = models.CharField(max_length=255, verbose_name="C variant")
    option_d = models.CharField(max_length=255, verbose_name="D variant")
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES, verbose_name="To'g'ri javob")

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        return f"{self.quiz.title} — {self.text[:40]}"


class QuizResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_results', verbose_name="O'quvchi")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results', verbose_name="Test")
    score = models.IntegerField(verbose_name="To'g'ri javoblar soni")
    total_questions = models.IntegerField(verbose_name="Jami savollar soni")
    percentage = models.FloatField(verbose_name="Foiz (%)")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        ordering = ['-percentage', '-completed_at']

    def __str__(self):
        return f"{self.student} — {self.quiz.title}: {self.percentage}%"
