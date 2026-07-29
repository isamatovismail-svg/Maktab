from django import forms
from .models import Student, Lesson


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Dilnoza'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Yusupova'}),
            'phone': forms.TextInput(attrs={'placeholder': '+998 90 123 45 67'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'teacher_name']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Python asoslari'}),
            'teacher_name': forms.TextInput(attrs={'placeholder': 'Aziz Karimov'}),
        }
