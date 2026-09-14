from django import forms
from django.contrib.auth.models import User
from .models import (
    Student, ParentProfile, Teacher, Subject, GradeClass, Homework,
    HomeworkSubmission, Grade, Quiz, Question, Timetable, FeeType,
    StudentFee, PaymentRecord, Exam, ExamResult, Announcement
)

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'gender', 'grade_class',
            'phone', 'address', 'parent', 'parent_phone', 'emergency_contact',
            'status', 'profile_photo', 'telegram_id'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ismi'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiyasi'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Yashash manzili...'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998909876543'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shoshilinch aloqa kishi va telefon'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'telegram_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456789'}),
        }


class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ['first_name', 'last_name', 'phone', 'email', 'occupation', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ismi'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiyasi'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ish joyi / kasbi'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Manzil'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matematika'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MATH101'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '📐'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }


class GradeClassForm(forms.ModelForm):
    class Meta:
        model = GradeClass
        fields = ['name', 'class_teacher']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9-A'}),
            'class_teacher': forms.Select(attrs={'class': 'form-select'}),
        }


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['grade_class', 'subject', 'teacher', 'day_of_week', 'time_slot', 'room']
        widgets = {
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'time_slot': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08:30 - 09:15'}),
            'room': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '101-xona'}),
        }


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ['grade_class', 'subject', 'teacher', 'title', 'description', 'attachment', 'due_date']
        widgets = {
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masalan, 45-bet 1-4 mashqlar'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Vazifa topshirig\'i...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class HomeworkSubmissionForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ['submission_text', 'attachment']
        widgets = {
            'submission_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Javobingiz va izohingiz...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'score', 'grade_type', 'date', 'comment']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5', 'min': 1, 'max': 100}),
            'grade_type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'comment': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Darsdagi faolligi uchun'}),
        }


class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'amount', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Oylik kontrakt to'lovi"}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '500000'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StudentFeeForm(forms.ModelForm):
    class Meta:
        model = StudentFee
        fields = ['student', 'fee_type', 'amount', 'discount_amount', 'due_date', 'academic_year']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'fee_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2026-2027'}),
        }


class PaymentRecordForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ['paid_amount', 'payment_method', 'transaction_id', 'note']
        widgets = {
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '500000'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tranzaksiya ID (ixtiyoriy)'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': "To'lov haqida izoh..."}),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'subject', 'grade_class', 'exam_date', 'total_marks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-Chorak Yakuniy Imtihoni'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100'}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'target_role', 'grade_class']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "E'lon sarlavhasi"}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': "E'lon matni..."}),
            'target_role': forms.Select(attrs={'class': 'form-select'}),
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
        }


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Parol"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Parolni tasdiqlang"
    )
    role = forms.ChoiceField(
        choices=[
            ('STUDENT', "O'quvchi"),
            ('TEACHER', "O'qituvchi"),
            ('PARENT', "Ota-ona"),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Rolingiz"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ismingiz'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiyangiz'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Parollar mos kelmadi!")
        return cleaned_data
