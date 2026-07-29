from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Student, Lesson
from .forms import StudentForm, LessonForm


# 1. LOGIN
class UserLoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            return redirect('student_list')
        return render(request, 'login.html', {'error': 'Username yoki parol noto\'g\'ri!'})


# 2. LOGOUT
class UserLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


# 3. TALABALAR RO'YXATI (READ)
class StudentListView(LoginRequiredMixin, View):
    def get(self, request):
        students = Student.objects.all()
        return render(request, 'students.html', {'students': students})


# 4. TALABA QO'SHISH (CREATE)
class StudentCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'student_form.html', {'form': StudentForm()})

    def post(self, request):
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
        return render(request, 'student_form.html', {'form': form})


# 5. TALABANI TAHRIRLASH (UPDATE)
class StudentUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_form.html', {'form': StudentForm(instance=student)})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('student_list')
        return render(request, 'student_form.html', {'form': form})


# 6. TALABANI O'CHIRISH (DELETE)
class StudentDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_delete.html', {'student': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        student.delete()
        return redirect('student_list')


# 7. DARSLAR RO'YXATI (READ)
class LessonListView(LoginRequiredMixin, View):
    def get(self, request):
        lessons = Lesson.objects.all()
        return render(request, 'lessons.html', {'lessons': lessons})


# 8. DARS QO'SHISH (CREATE)
class LessonCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'lesson_form.html', {'form': LessonForm()})

    def post(self, request):
        form = LessonForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lesson_list')
        return render(request, 'lesson_form.html', {'form': form})


# 9. DARSNI TAHRIRLASH (UPDATE)
class LessonUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        return render(request, 'lesson_form.html', {'form': LessonForm(instance=lesson)})

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('lesson_list')
        return render(request, 'lesson_form.html', {'form': form})


# 10. DARSNI O'CHIRISH (DELETE)
class LessonDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        return render(request, 'lesson_delete.html', {'lesson': lesson})

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        lesson.delete()
        return redirect('lesson_list')