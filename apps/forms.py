from django import forms
from django.contrib.auth.models import User
from .models import (
    Student, Teacher, Subject, GradeClass, Homework,
    HomeworkSubmission, Grade, Lesson, Quiz, Question, Timetable, FeeType,
    StudentFee, PaymentRecord, Exam, ExamResult, Announcement
)

# ── Yordamchi funksiyalar ─────────────────────────────────────

def fc(placeholder=None, **extra):
    """form-control widget attrs yordamchisi."""
    attrs = {'class': 'form-control'}
    if placeholder:
        attrs['placeholder'] = placeholder
    attrs.update(extra)
    return attrs

def fs():
    """form-select widget attrs yordamchisi."""
    return {'class': 'form-select'}


# ── Formalar ──────────────────────────────────────────────────

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'gender', 'grade_class',
            'phone', 'address', 'parent_phone', 'emergency_contact',
            'status', 'profile_photo', 'telegram_id'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs=fc('Ismi')),
            'last_name': forms.TextInput(attrs=fc('Familiyasi')),
            'birth_date': forms.DateInput(attrs=fc(type='date')),
            'gender': forms.Select(attrs=fs()),
            'grade_class': forms.Select(attrs=fs()),
            'phone': forms.TextInput(attrs=fc('+998901234567')),
            'address': forms.Textarea(attrs=fc('Yashash manzili...', rows=2)),
            'parent_phone': forms.TextInput(attrs=fc('+998909876543')),
            'emergency_contact': forms.TextInput(attrs=fc('Shoshilinch aloqa kishi va telefon')),
            'status': forms.Select(attrs=fs()),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'telegram_id': forms.TextInput(attrs=fc('123456789')),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs=fc('Matematika')),
            'code': forms.TextInput(attrs=fc('MATH101')),
            'icon': forms.TextInput(attrs=fc('📐')),
            'color': forms.TextInput(attrs=fc(type='color')),
        }


class GradeClassForm(forms.ModelForm):
    class Meta:
        model = GradeClass
        fields = ['name', 'class_teacher']
        widgets = {
            'name': forms.TextInput(attrs=fc('9-A')),
            'class_teacher': forms.Select(attrs=fs()),
        }


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['first_name', 'last_name', 'subject', 'assigned_subjects', 'assigned_classes', 'phone', 'qualification', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs=fc('Ismi')),
            'last_name': forms.TextInput(attrs=fc('Familiyasi')),
            'subject': forms.Select(attrs=fs()),
            'assigned_subjects': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'assigned_classes': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'phone': forms.TextInput(attrs=fc('+998901234567')),
            'qualification': forms.TextInput(attrs=fc('Oliy toifali')),
            'bio': forms.Textarea(attrs=fc('Qisqacha bio...', rows=3)),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'subject', 'teacher', 'grade_class', 'date', 'description']
        widgets = {
            'title': forms.TextInput(attrs=fc('Dars mavzusi sarlavhasi')),
            'subject': forms.Select(attrs=fs()),
            'teacher': forms.Select(attrs=fs()),
            'grade_class': forms.Select(attrs=fs()),
            'date': forms.DateInput(attrs=fc(type='date')),
            'description': forms.Textarea(attrs=fc("Dars haqida batafsil ma'lumot...", rows=3)),
        }


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['grade_class', 'subject', 'teacher', 'day_of_week', 'time_slot', 'room']
        widgets = {
            'grade_class': forms.Select(attrs=fs()),
            'subject': forms.Select(attrs=fs()),
            'teacher': forms.Select(attrs=fs()),
            'day_of_week': forms.Select(attrs=fs()),
            'time_slot': forms.TextInput(attrs=fc('08:30 - 09:15')),
            'room': forms.TextInput(attrs=fc('101-xona')),
        }


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ['grade_class', 'subject', 'teacher', 'title', 'description', 'attachment', 'due_date']
        widgets = {
            'grade_class': forms.Select(attrs=fs()),
            'subject': forms.Select(attrs=fs()),
            'teacher': forms.Select(attrs=fs()),
            'title': forms.TextInput(attrs=fc('Masalan, 45-bet 1-4 mashqlar')),
            'description': forms.Textarea(attrs=fc("Vazifa topshirig'i...", rows=3)),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs=fc(type='date')),
        }


class HomeworkSubmissionForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ['submission_text', 'attachment']
        widgets = {
            'submission_text': forms.Textarea(attrs=fc('Javobingiz va izohingiz...', rows=4)),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'teacher', 'subject', 'lesson', 'score', 'grade_type', 'date', 'comment']
        widgets = {
            'student': forms.Select(attrs=fs()),
            'teacher': forms.Select(attrs=fs()),
            'subject': forms.Select(attrs=fs()),
            'lesson': forms.Select(attrs=fs()),
            'score': forms.NumberInput(attrs=fc('5', min=1, max=100)),
            'grade_type': forms.Select(attrs=fs()),
            'date': forms.DateInput(attrs=fc(type='date')),
            'comment': forms.TextInput(attrs=fc('Darsdagi faolligi uchun')),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].required = False
        self.fields['lesson'].required = False



class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'amount', 'description']
        widgets = {
            'name': forms.TextInput(attrs=fc("Oylik kontrakt to'lovi")),
            'amount': forms.NumberInput(attrs=fc('500000')),
            'description': forms.Textarea(attrs=fc(rows=2)),
        }


class StudentFeeForm(forms.ModelForm):
    class Meta:
        model = StudentFee
        fields = ['student', 'fee_type', 'amount', 'discount_amount', 'due_date', 'academic_year']
        widgets = {
            'student': forms.Select(attrs=fs()),
            'fee_type': forms.Select(attrs=fs()),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs=fc('0')),
            'due_date': forms.DateInput(attrs=fc(type='date')),
            'academic_year': forms.TextInput(attrs=fc('2026-2027')),
        }


class PaymentRecordForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ['paid_amount', 'payment_method', 'transaction_id', 'note']
        widgets = {
            'paid_amount': forms.NumberInput(attrs=fc('500000')),
            'payment_method': forms.Select(attrs=fs()),
            'transaction_id': forms.TextInput(attrs=fc('Tranzaksiya ID (ixtiyoriy)')),
            'note': forms.Textarea(attrs=fc("To'lov haqida izoh...", rows=2)),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'subject', 'grade_class', 'exam_date', 'total_marks']
        widgets = {
            'title': forms.TextInput(attrs=fc('1-Chorak Yakuniy Imtihoni')),
            'subject': forms.Select(attrs=fs()),
            'grade_class': forms.Select(attrs=fs()),
            'exam_date': forms.DateInput(attrs=fc(type='date')),
            'total_marks': forms.NumberInput(attrs=fc('100')),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'target_role', 'grade_class']
        widgets = {
            'title': forms.TextInput(attrs=fc("E'lon sarlavhasi")),
            'content': forms.Textarea(attrs=fc("E'lon matni...", rows=4)),
            'target_role': forms.Select(attrs=fs()),
            'grade_class': forms.Select(attrs=fs()),
        }


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=fc('••••••••')),
        label="Parol"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs=fc('••••••••')),
        label="Parolni tasdiqlang"
    )
    role = forms.ChoiceField(
        choices=[('STUDENT', "O'quvchi"), ('TEACHER', "O'qituvchi")],
        widget=forms.Select(attrs=fs()),
        label="Rolingiz"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs=fc('username')),
            'first_name': forms.TextInput(attrs=fc('Ismingiz')),
            'last_name': forms.TextInput(attrs=fc('Familiyangiz')),
            'email': forms.EmailInput(attrs=fc('email@example.com')),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1, p2 = cleaned_data.get('password'), cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Parollar mos kelmadi!")
        return cleaned_data
