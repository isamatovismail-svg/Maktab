from django import forms
from django.contrib.auth.models import User
from .models import Student, Subject, GradeClass, Homework, Grade, Quiz, Question, Teacher

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'grade_class', 'phone', 'parent_phone', 'telegram_id']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ismi'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiyasi'}),
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998901234567'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998909876543'}),
            'telegram_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456789 (ixtiyoriy)'}),
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


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ['grade_class', 'subject', 'title', 'description', 'due_date']
        widgets = {
            'grade_class': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masalan, 45-betdagi 1-4 mashqlar'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Vazifa haqida batafsil...'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Parol"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Parolni tasdiqlang"
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
