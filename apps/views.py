from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
import datetime

from .models import Student, Lesson, Attendance
from .forms import StudentForm, LessonForm


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


class UserLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


class StudentListView(LoginRequiredMixin, View):
    def get(self, request):
        students = Student.objects.all()
        return render(request, 'students.html', {'students': students})


class StudentCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'student_form.html', {'form': StudentForm()})

    def post(self, request):
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
        return render(request, 'student_form.html', {'form': form})


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


class StudentDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_delete.html', {'student': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        student.delete()
        return redirect('student_list')


class LessonListView(LoginRequiredMixin, View):
    def get(self, request):
        lessons = Lesson.objects.all()
        return render(request, 'lessons.html', {'lessons': lessons})


class LessonCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'lesson_form.html', {'form': LessonForm()})

    def post(self, request):
        form = LessonForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lesson_list')
        return render(request, 'lesson_form.html', {'form': form})


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


class LessonDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        return render(request, 'lesson_delete.html', {'lesson': lesson})

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        lesson.delete()
        return redirect('lesson_list')


class AttendanceSelectView(LoginRequiredMixin, View):
    def get(self, request):
        lessons = Lesson.objects.all()
        today = datetime.date.today().isoformat()
        return render(request, 'attendance_select.html', {'lessons': lessons, 'today': today})

    def post(self, request):
        lesson_id = request.POST.get('lesson_id')
        date = request.POST.get('date')
        if lesson_id and date:
            return redirect('attendance_mark', lesson_id=lesson_id, date=date)
        lessons = Lesson.objects.all()
        today = datetime.date.today().isoformat()
        return render(request, 'attendance_select.html', {'lessons': lessons, 'today': today, 'error': ""})


class AttendanceMarkView(LoginRequiredMixin, View):
    def get(self, request, lesson_id, date):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        try:
            date_obj = datetime.date.fromisoformat(date)
        except ValueError:
            return redirect('attendance_select')
        students = Student.objects.all()
        existing = {a.student_id: a.status for a in Attendance.objects.filter(lesson=lesson, date=date_obj)}
        rows = []
        for s in students:
            rows.append({'student': s, 'status': existing.get(s.pk, '')})
        return render(request, 'attendance_mark.html', {
            'lesson': lesson,
            'date': date_obj,
            'rows': rows,
        })

    def post(self, request, lesson_id, date):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        try:
            date_obj = datetime.date.fromisoformat(date)
        except ValueError:
            return redirect('attendance_select')
        students = Student.objects.all()
        for s in students:
            status = request.POST.get(f'status_{s.pk}', '')
            if status in ('B', 'K', 'Y'):
                Attendance.objects.update_or_create(
                    student=s, lesson=lesson, date=date_obj,
                    defaults={'status': status}
                )
        return redirect('attendance_mark', lesson_id=lesson_id, date=date)