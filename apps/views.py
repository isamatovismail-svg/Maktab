from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
import datetime

from .models import (
    GradeClass, Subject, Teacher, Student, Timetable, 
    Grade, Attendance, Homework, Quiz, Question, QuizResult
)
from .forms import (
    StudentForm, SubjectForm, GradeClassForm, 
    HomeworkForm, GradeForm, RegisterForm
)

# ──────────────────────────────────────────────────────────────
# Authentication Views
# ──────────────────────────────────────────────────────────────

class UserLoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        username = (request.POST.get('username') or '').strip()
        password = (request.POST.get('password') or '').strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        return render(request, 'login.html', {'error': 'Username yoki parol noto\'g\'ri!'})



class UserLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


class UserRegisterView(View):
    def get(self, request):
        return render(request, 'register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('home')
        return render(request, 'register.html', {'form': form})


# ──────────────────────────────────────────────────────────────
# Dashboard / Home View
# ──────────────────────────────────────────────────────────────

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_classes = GradeClass.objects.count()
        total_subjects = Subject.objects.count()
        total_quizzes = Quiz.objects.count()

        recent_grades = Grade.objects.select_related('student', 'subject').all()[:6]
        today_num = datetime.date.today().isoweekday()  # 1..7
        today_timetables = Timetable.objects.filter(day_of_week=today_num).select_related('grade_class', 'subject', 'teacher')[:6]

        # Top 5 students by quiz performance
        top_students = Student.objects.annotate(
            avg_score=Avg('quiz_results__percentage')
        ).filter(avg_score__isnull=False).order_by('-avg_score')[:5]

        return render(request, 'home.html', {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_classes': total_classes,
            'total_subjects': total_subjects,
            'total_quizzes': total_quizzes,
            'recent_grades': recent_grades,
            'today_timetables': today_timetables,
            'top_students': top_students,
            'today_date': datetime.date.today(),
        })


# ──────────────────────────────────────────────────────────────
# O'quvchilar Boshqaruvi
# ──────────────────────────────────────────────────────────────

class StudentListView(LoginRequiredMixin, View):
    def get(self, request):
        class_id = request.GET.get('class_id')
        search_query = request.GET.get('q', '')

        students = Student.objects.select_related('grade_class').all()
        if class_id:
            students = students.filter(grade_class_id=class_id)
        if search_query:
            students = students.filter(
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) | 
                Q(phone__icontains=search_query)
            )

        classes = GradeClass.objects.all()
        return render(request, 'students.html', {
            'students': students,
            'classes': classes,
            'selected_class': class_id,
            'search_query': search_query,
        })


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


# ──────────────────────────────────────────────────────────────
# Elektron Kundalik — Baholar Jurnali
# ──────────────────────────────────────────────────────────────

class GradeBookView(LoginRequiredMixin, View):
    def get(self, request):
        classes = GradeClass.objects.all()
        subjects = Subject.objects.all()

        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')

        students = []
        grades_matrix = {}
        if selected_class_id:
            students = Student.objects.filter(grade_class_id=selected_class_id)
            grades_qs = Grade.objects.filter(student__in=students)
            if selected_subject_id:
                grades_qs = grades_qs.filter(subject_id=selected_subject_id)

            for g in grades_qs:
                if g.student_id not in grades_matrix:
                    grades_matrix[g.student_id] = []
                grades_matrix[g.student_id].append(g)

        return render(request, 'grades.html', {
            'classes': classes,
            'subjects': subjects,
            'selected_class_id': selected_class_id,
            'selected_subject_id': selected_subject_id,
            'students': students,
            'grades_matrix': grades_matrix,
            'grade_form': GradeForm(),
        })

    def post(self, request):
        form = GradeForm(request.POST)
        if form.is_valid():
            form.save()
            c_id = form.cleaned_data['student'].grade_class_id
            s_id = form.cleaned_data['subject'].id
            return redirect(f'/grades/?class_id={c_id}&subject_id={s_id}')
        return redirect('gradebook')


# ──────────────────────────────────────────────────────────────
# Yo'qlama / Davomat Tizimi
# ──────────────────────────────────────────────────────────────

class AttendanceView(LoginRequiredMixin, View):
    def get(self, request):
        classes = GradeClass.objects.all()
        subjects = Subject.objects.all()

        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')
        selected_date = request.GET.get('date', datetime.date.today().isoformat())

        students = []
        existing_status = {}
        if selected_class_id and selected_subject_id:
            students = Student.objects.filter(grade_class_id=selected_class_id)
            attendances = Attendance.objects.filter(
                subject_id=selected_subject_id,
                date=selected_date,
                student__in=students
            )
            existing_status = {a.student_id: a.status for a in attendances}

        return render(request, 'attendance.html', {
            'classes': classes,
            'subjects': subjects,
            'selected_class_id': selected_class_id,
            'selected_subject_id': selected_subject_id,
            'selected_date': selected_date,
            'students': students,
            'existing_status': existing_status,
        })

    def post(self, request):
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')
        date_str = request.POST.get('date')

        if class_id and subject_id and date_str:
            students = Student.objects.filter(grade_class_id=class_id)
            subject = get_object_or_404(Subject, pk=subject_id)
            for s in students:
                status = request.POST.get(f'status_{s.id}', 'B')
                Attendance.objects.update_or_create(
                    student=s, subject=subject, date=date_str,
                    defaults={'status': status}
                )
        return redirect(f'/attendance/?class_id={class_id}&subject_id={subject_id}&date={date_str}')


# ──────────────────────────────────────────────────────────────
# Dars Jadvali & Uyga Vazifalar
# ──────────────────────────────────────────────────────────────

class TimetableView(LoginRequiredMixin, View):
    def get(self, request):
        classes = GradeClass.objects.all()
        selected_class_id = request.GET.get('class_id', classes.first().id if classes.exists() else None)

        schedule_by_day = {}
        if selected_class_id:
            for day_num, day_name in Timetable.DAYS:
                schedule_by_day[day_name] = Timetable.objects.filter(
                    grade_class_id=selected_class_id,
                    day_of_week=day_num
                ).select_related('subject', 'teacher')

        return render(request, 'timetable.html', {
            'classes': classes,
            'selected_class_id': int(selected_class_id) if selected_class_id else None,
            'schedule_by_day': schedule_by_day,
        })


class HomeworkListView(LoginRequiredMixin, View):
    def get(self, request):
        homeworks = Homework.objects.select_related('grade_class', 'subject').all()
        form = HomeworkForm()
        return render(request, 'homework.html', {'homeworks': homeworks, 'form': form})

    def post(self, request):
        form = HomeworkForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('homework_list')
        homeworks = Homework.objects.select_related('grade_class', 'subject').all()
        return render(request, 'homework.html', {'homeworks': homeworks, 'form': form})


# ──────────────────────────────────────────────────────────────
# Bilim.uz Test Platformasi Views
# ──────────────────────────────────────────────────────────────

class QuizListView(LoginRequiredMixin, View):
    def get(self, request):
        quizzes = Quiz.objects.select_related('subject').annotate(num_questions=Count('questions')).all()
        return render(request, 'quizzes.html', {'quizzes': quizzes})


class QuizTakeView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        questions = quiz.questions.all()
        students = Student.objects.all()
        return render(request, 'quiz_take.html', {
            'quiz': quiz,
            'questions': questions,
            'students': students,
        })

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        questions = quiz.questions.all()
        student_id = request.POST.get('student_id')
        if not student_id:
            student = Student.objects.first()
        else:
            student = get_object_or_404(Student, pk=student_id)

        correct_count = 0
        total_questions = questions.count()

        for q in questions:
            user_ans = request.POST.get(f'q_{q.id}')
            if user_ans and user_ans == q.correct_option:
                correct_count += 1

        percentage = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0

        result = QuizResult.objects.create(
            student=student,
            quiz=quiz,
            score=correct_count,
            total_questions=total_questions,
            percentage=percentage
        )

        return render(request, 'quiz_result.html', {
            'result': result,
            'quiz': quiz,
        })


class LeaderboardView(LoginRequiredMixin, View):
    def get(self, request):
        results = QuizResult.objects.select_related('student', 'quiz').order_by('-percentage', '-score')[:20]
        return render(request, 'leaderboard.html', {'results': results})