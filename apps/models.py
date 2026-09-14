from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .permissions import Role

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.CHOICES, default=Role.STUDENT, db_index=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    address = models.TextField(blank=True, verbose_name="Manzil")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Avatar")

    class Meta:
        verbose_name = "Foydalanuvchi Profili"
        verbose_name_plural = "Foydalanuvchi Profilari"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class GradeClass(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Sinf nomi")  # e.g., 9-A, 10-B
    class_teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_classes', verbose_name="Sinf rahbari"
    )

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


class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile', null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqami")
    email = models.EmailField(blank=True, verbose_name="Email")
    occupation = models.CharField(max_length=100, blank=True, verbose_name="Kasbi / Ish joyi")
    address = models.TextField(blank=True, verbose_name="Yashash manzili")

    class Meta:
        verbose_name = "Ota-ona (Vasiy)"
        verbose_name_plural = "Ota-onalar (Vasiylar)"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile', null=True, blank=True)
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers', verbose_name="Bosh fani")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqami")
    qualification = models.CharField(max_length=150, blank=True, verbose_name="Ma'lumoti / Malaka toifasi")
    bio = models.TextField(blank=True, verbose_name="Qisqacha ma'lumot")

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.subject or 'Fansiz'})"


class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Erkak'),
        ('F', 'Ayol'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Faol'),
        ('INACTIVE', 'Nofaol'),
        ('GRADUATED', 'Bitirgan'),
        ('TRANSFERRED', "Ko'chirilgan"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', null=True, blank=True)
    student_id = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name="O'quvchi ID kodi")
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan sana")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M', verbose_name="Jinsi")
    grade_class = models.ForeignKey(GradeClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Sinf", db_index=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name="O'quvchi telefoni")
    address = models.TextField(blank=True, verbose_name="Yashash manzili")
    
    parent = models.ForeignKey(ParentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name="Ota-onasi / Vasiy")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Ota-onasining telefoni")
    emergency_contact = models.CharField(max_length=100, blank=True, verbose_name="Shoshilinch aloqa raqami")
    
    admission_date = models.DateField(default=timezone.now, verbose_name="Qabul qilingan sana")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Holati", db_index=True)
    profile_photo = models.ImageField(upload_to='students/photos/', null=True, blank=True, verbose_name="Profil rasmi")
    telegram_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telegram Chat ID", db_index=True)

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.grade_class or 'Sinfsiz'})"

    def save(self, *args, **kwargs):
        if not self.student_id:
            import random
            prefix = "STU"
            rand_num = random.randint(10000, 99999)
            self.student_id = f"{prefix}-{rand_num}"
        super().save(*args, **kwargs)


class Timetable(models.Model):
    DAYS = [
        (1, 'Dushanba'),
        (2, 'Seshanba'),
        (3, 'Chorshanba'),
        (4, 'Payshanba'),
        (5, 'Juma'),
        (6, 'Shanba'),
    ]
    grade_class = models.ForeignKey(GradeClass, on_delete=models.CASCADE, related_name='timetables', verbose_name="Sinf", db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="O'qituvchi", db_index=True)
    day_of_week = models.IntegerField(choices=DAYS, verbose_name="Hafta kuni", db_index=True)
    time_slot = models.CharField(max_length=50, verbose_name="Vaqti (masalan, 08:30 - 09:15)")
    room = models.CharField(max_length=50, blank=True, verbose_name="Xona")

    class Meta:
        verbose_name = "Dars Jadvali"
        verbose_name_plural = "Dars Jadvallari"
        ordering = ['day_of_week', 'time_slot']

    def __str__(self):
        return f"{self.grade_class} — {self.get_day_of_week_display()} — {self.subject}"

    def clean(self):
        super().clean()
        # Teacher conflict check
        if self.teacher and self.day_of_week and self.time_slot:
            conflict_teacher = Timetable.objects.filter(
                teacher=self.teacher,
                day_of_week=self.day_of_week,
                time_slot=self.time_slot
            ).exclude(pk=self.pk)
            if conflict_teacher.exists():
                other = conflict_teacher.first()
                raise ValidationError(
                    f"Xatolik: O'qituvchi ({self.teacher}) {self.get_day_of_week_display()} kuni {self.time_slot} vaqtida {other.grade_class} sinfida darsda!"
                )

        # Room conflict check
        if self.room and self.day_of_week and self.time_slot:
            conflict_room = Timetable.objects.filter(
                room__iexact=self.room,
                day_of_week=self.day_of_week,
                time_slot=self.time_slot
            ).exclude(pk=self.pk)
            if conflict_room.exists():
                other = conflict_room.first()
                raise ValidationError(
                    f"Xatolik: Xona ({self.room}) {self.get_day_of_week_display()} kuni {self.time_slot} vaqtida {other.grade_class} sinfi tomonidan band qilingan!"
                )


class Grade(models.Model):
    GRADE_TYPES = [
        ('KUNDALIK', 'Kundalik dars'),
        ('NAZORAT', 'Nazorat ishi'),
        ('CHORAK', 'Choraklik baho'),
        ('HOMEWORK', 'Uyga vazifa'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades', verbose_name="O'quvchi", db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades', verbose_name="Fan", db_index=True)
    score = models.IntegerField(verbose_name="Baho (1-5 yoki 1-100)")
    grade_type = models.CharField(max_length=20, choices=GRADE_TYPES, default='KUNDALIK', verbose_name="Baho turi")
    date = models.DateField(verbose_name="Sana", db_index=True)
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
        ('B', 'Bor (Present)'),
        ('K', 'Kech qoldi (Late)'),
        ('Y', "Yo'q (Absent)"),
        ('S', "Sababli yo'q (Excused)"),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances', verbose_name="O'quvchi", db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances', verbose_name="Fan", db_index=True)
    date = models.DateField(verbose_name="Sana", db_index=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='B', verbose_name="Holat", db_index=True)
    notified_telegram = models.BooleanField(default=False, verbose_name="Telegramga yuborildi")

    class Meta:
        unique_together = ('student', 'subject', 'date')
        verbose_name = "Yo'qlama"
        verbose_name_plural = "Yo'qlamalar"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} — {self.subject} — {self.date} — {self.status}"


class FeeType(models.Model):
    name = models.CharField(max_length=100, verbose_name="To'lov turi nomi")  # e.g., Oylik kontrakti, Qabul to'lovi
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Standart summa (UZS)")
    description = models.TextField(blank=True, verbose_name="Tavsif")

    class Meta:
        verbose_name = "To'lov Turi"
        verbose_name_plural = "To'lov Turlari"

    def __str__(self):
        return f"{self.name} ({self.amount:,.0f} UZS)"


class StudentFee(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('PAID', "To'langan"),
        ('PARTIAL', "Qisman to'langan"),
        ('OVERDUE', 'Muddati o\'tgan'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees', verbose_name="O'quvchi", db_index=True)
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, verbose_name="To'lov turi")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Belgilangan summa (UZS)")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Chegirma / Imtiyoz (UZS)")
    due_date = models.DateField(verbose_name="Topshirish ohirgi muddati", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Holat", db_index=True)
    academic_year = models.CharField(max_length=20, default="2026-2027", verbose_name="O'quv yili")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O'quvchi To'lovi"
        verbose_name_plural = "O'quvchilar To'lovlari"
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.student} — {self.fee_type.name}: {self.net_amount:,.0f} UZS ({self.get_status_display()})"

    @property
    def net_amount(self):
        return max(0, float(self.amount) - float(self.discount_amount))

    @property
    def total_paid(self):
        paid = self.payments.aggregate(total=models.Sum('paid_amount'))['total'] or 0
        return float(paid)

    @property
    def balance_due(self):
        return max(0, self.net_amount - self.total_paid)

    def update_status(self):
        if self.balance_due <= 0:
            self.status = 'PAID'
        elif self.total_paid > 0:
            self.status = 'PARTIAL'
        elif self.due_date < timezone.now().date():
            self.status = 'OVERDUE'
        else:
            self.status = 'PENDING'
        self.save()


class PaymentRecord(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Naqd pul'),
        ('CARD', 'Bank kartasi (Click/Payme)'),
        ('BANK', 'Bank o\'tkazmasi'),
    ]
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='payments', verbose_name="To'lov hujjati")
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To'langan summa (UZS)")
    payment_date = models.DateField(default=timezone.now, verbose_name="To'lov sanasi")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CARD', verbose_name="To'lov usuli")
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name="Tranzaksiya ID")
    receipt_number = models.CharField(max_length=50, unique=True, verbose_name="Kvitansiya / Chek raqami")
    note = models.TextField(blank=True, verbose_name="Qo'shimcha izoh")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "To'lov Yozuvi"
        verbose_name_plural = "To'lov Yozuvlari"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Chek #{self.receipt_number} — {self.paid_amount:,.0f} UZS ({self.payment_date})"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            import random
            self.receipt_number = f"REC-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)
        self.student_fee.update_status()


class Homework(models.Model):
    grade_class = models.ForeignKey(GradeClass, on_delete=models.CASCADE, related_name='homeworks', verbose_name="Sinf", db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="O'qituvchi")
    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    description = models.TextField(verbose_name="Vazifa topshirig'i")
    attachment = models.FileField(upload_to='homeworks/attachments/', null=True, blank=True, verbose_name="Ilova fayl")
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(verbose_name="Topshirish muddati", db_index=True)

    class Meta:
        verbose_name = "Uyga vazifa"
        verbose_name_plural = "Uyga vazifalar"
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.grade_class} — {self.subject}: {self.title}"


class HomeworkSubmission(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Kutilmoqda'),
        ('SUBMITTED', 'Topshirildi'),
        ('GRADED', 'Baholandi'),
        ('LATE', 'Kechikkan'),
    ]
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions', verbose_name="Uyga vazifa")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='homework_submissions', verbose_name="O'quvchi")
    submission_text = models.TextField(blank=True, verbose_name="Javob matni")
    attachment = models.FileField(upload_to='homeworks/submissions/', null=True, blank=True, verbose_name="Bajarilgan vazifa fayli")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Topshirilgan vaqt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED', verbose_name="Holati")
    score = models.IntegerField(null=True, blank=True, verbose_name="Baho (1-100)")
    teacher_feedback = models.TextField(blank=True, verbose_name="O'qituvchi fikri")

    class Meta:
        unique_together = ('homework', 'student')
        verbose_name = "Vazifa Topshirig'i"
        verbose_name_plural = "Vazifa Topshiriqlari"

    def __str__(self):
        return f"{self.student} — {self.homework.title} ({self.get_status_display()})"


class Exam(models.Model):
    title = models.CharField(max_length=200, verbose_name="Imtihon nomi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Fan")
    grade_class = models.ForeignKey(GradeClass, on_delete=models.CASCADE, related_name='exams', verbose_name="Sinf")
    exam_date = models.DateField(verbose_name="Imtihon o'tkazilish sanasi")
    total_marks = models.IntegerField(default=100, verbose_name="Maksimal ball")

    class Meta:
        verbose_name = "Imtihon"
        verbose_name_plural = "Imtihonlar"
        ordering = ['-exam_date']

    def __str__(self):
        return f"{self.title} — {self.grade_class} ({self.subject})"


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results', verbose_name="Imtihon")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results', verbose_name="O'quvchi")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="To'plangan ball")
    percentage = models.FloatField(verbose_name="Foiz (%)")
    grade = models.CharField(max_length=5, verbose_name="Baho / Daraja (5,4,3,2 yoki A,B,C)")
    rank = models.IntegerField(null=True, blank=True, verbose_name="Sinfdagi o'rni")
    teacher_comments = models.CharField(max_length=255, blank=True, verbose_name="O'qituvchi izohi")

    class Meta:
        unique_together = ('exam', 'student')
        verbose_name = "Imtihon Natijasi"
        verbose_name_plural = "Imtihon Natijalari"
        ordering = ['-percentage']

    def __str__(self):
        return f"{self.student} — {self.exam.title}: {self.marks_obtained}/{self.exam.total_marks} ({self.percentage}%)"

    def save(self, *args, **kwargs):
        if self.exam and self.marks_obtained is not None:
            self.percentage = round((float(self.marks_obtained) / float(self.exam.total_marks)) * 100, 1)
            if self.percentage >= 85:
                self.grade = '5'
            elif self.percentage >= 70:
                self.grade = '4'
            elif self.percentage >= 55:
                self.grade = '3'
            else:
                self.grade = '2'
        super().save(*args, **kwargs)


class Announcement(models.Model):
    TARGET_ROLES = [
        ('ALL', "Barcha foydalanuvchilar"),
        ('TEACHERS', "Faqat o'qituvchilar"),
        ('STUDENTS', "Faqat o'quvchilar"),
        ('PARENTS', "Faqat ota-onalar"),
    ]
    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    content = models.TextField(verbose_name="E'lon matni")
    target_role = models.CharField(max_length=20, choices=TARGET_ROLES, default='ALL', verbose_name="Mo'ljallangan auditoriya")
    grade_class = models.ForeignKey(GradeClass, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Muayyan sinf uchun")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Muallif")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_target_role_display()})"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('HOMEWORK', 'Uyga vazifa'),
        ('EXAM', 'Imtihon'),
        ('FEE', "To'lov eslatmasi"),
        ('ATTENDANCE', 'Davomat'),
        ('ANNOUNCEMENT', "E'lon"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Foydalanuvchi")
    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ANNOUNCEMENT', verbose_name="Turi")
    link = models.CharField(max_length=255, blank=True, verbose_name="Havola")
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.title} ({'O\'qilgan' if self.is_read else 'Yangi'})"


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
