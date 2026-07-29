from django import forms
from .models import Student, Lesson

class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class StudentForm(BootstrapModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name', 'phone']

class LessonForm(BootstrapModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'teacher_name']

