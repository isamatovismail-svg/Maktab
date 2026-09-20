import datetime
import logging
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib import messages

from .models import (
    UserProfile, GradeClass, Subject, ParentProfile, Teacher, Student,
    Timetable, Lesson, Grade, Attendance, FeeType, StudentFee, PaymentRecord,
    Homework, HomeworkSubmission, Exam, ExamResult, Announcement,
    Notification, Quiz, Question, QuizResult
)
from .forms import (
    StudentForm, TeacherForm, SubjectForm, GradeClassForm, LessonForm, TimetableForm,
    HomeworkForm, HomeworkSubmissionForm, GradeForm, FeeTypeForm, StudentFeeForm,
    PaymentRecordForm, ExamForm, AnnouncementForm, RegisterForm
)
from .permissions import Role, RoleRequiredMixin, get_user_role, role_required
from .utils import send_system_notification, export_queryset_to_csv

logger = logging.getLogger('apps')


# ── Autentifikatsiya ──────────────────────────────────────────

class UserLoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'login.html')

    def post(self, request):
        username = (request.POST.get('username') or '').strip()
        password = (request.POST.get('password') or '').strip()
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            logger.info(f"User login: {username}")
            return redirect('home')
        logger.warning(f"Login failed: {username}")
        return render(request, 'login.html', {'error': "Username yoki parol noto'g'ri!"})


class UserLogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            logger.info(f"User logout: {request.user.username}")
            logout(request)
        return redirect('login')


class UserRegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'register.html', {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            role = form.cleaned_data.get('role', Role.STUDENT)
            UserProfile.objects.create(user=user, role=role)
            if role == Role.STUDENT:
                Student.objects.create(user=user, first_name=user.first_name or user.username, last_name=user.last_name or '')
            elif role == Role.TEACHER:
                Teacher.objects.create(user=user, first_name=user.first_name or user.username, last_name=user.last_name or '', phone='')
            login(request, user)
            messages.success(request, "Akkauntingiz muvaffaqiyatli yaratildi!")
            return redirect('home')
        return render(request, 'register.html', {'form': form})


# ── Dashboard (Bosh Sahifa) ───────────────────────────────────

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        role = get_user_role(user)
        today = datetime.date.today()

        context = {
            'today_date': today,
            'announcements': Announcement.objects.select_related('created_by').filter(
                Q(target_role='ALL') |
                (Q(target_role='TEACHERS') if role == Role.TEACHER else Q()) |
                (Q(target_role='STUDENTS') if role == Role.STUDENT else Q())
            )[:5],
        }

        # 1. STUDENT DASHBOARD
        if role == Role.STUDENT:
            student = getattr(user, 'student_profile', None) or Student.objects.filter(user=user).first()
            if student:
                grades = Grade.objects.filter(student=student).select_related('subject', 'teacher', 'lesson')[:10]
                attendances = Attendance.objects.filter(student=student).select_related('subject')[:5]
                lessons = Lesson.objects.filter(grade_class=student.grade_class).select_related('subject', 'teacher')[:5] if student.grade_class else []
                homeworks = Homework.objects.filter(grade_class=student.grade_class)[:5] if student.grade_class else []
                avg_score = grades.aggregate(avg=Avg('score'))['avg'] or 0
                context.update({
                    'student': student,
                    'student_grades': grades,
                    'student_attendances': attendances,
                    'student_lessons': lessons,
                    'student_homeworks': homeworks,
                    'avg_score': round(avg_score, 1),
                })
            return render(request, 'home.html', context)

        # 2. TEACHER DASHBOARD
        if role == Role.TEACHER:
            teacher = getattr(user, 'teacher_profile', None) or Teacher.objects.filter(user=user).first()
            if teacher:
                my_subjects = (Subject.objects.filter(pk=teacher.subject_id) if teacher.subject else Subject.objects.none()) | teacher.assigned_subjects.all()
                my_subjects = my_subjects.distinct()
                my_classes = teacher.assigned_classes.all()
                my_students = Student.objects.filter(grade_class__in=my_classes).distinct()
                my_lessons = Lesson.objects.filter(teacher=teacher).select_related('subject', 'grade_class')[:8]
                my_grades = Grade.objects.filter(teacher=teacher).select_related('student', 'subject', 'lesson')[:8]

                context.update({
                    'teacher': teacher,
                    'my_subjects': my_subjects,
                    'my_classes': my_classes,
                    'my_students_count': my_students.count(),
                    'my_lessons': my_lessons,
                    'my_grades': my_grades,
                })
            return render(request, 'home.html', context)

        # 3. ADMIN DASHBOARD
        context.update({
            'total_students': Student.objects.count(),
            'total_teachers': Teacher.objects.count(),
            'total_classes': GradeClass.objects.count(),
            'total_subjects': Subject.objects.count(),
            'total_lessons': Lesson.objects.count(),
            'total_grades': Grade.objects.count(),
            'today_timetables': Timetable.objects.filter(day_of_week=today.isoweekday()).select_related('grade_class', 'subject', 'teacher')[:6],
            'recent_grades': Grade.objects.select_related('student', 'subject', 'teacher').all()[:8],
            'monthly_revenue': PaymentRecord.objects.filter(payment_date__month=today.month).aggregate(total=Sum('paid_amount'))['total'] or 0,
        })
        return render(request, 'home.html', context)


# ── O'qituvchilar Boshqaruvi (Admin uchun) ───────────────────

class TeacherListView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def get(self, request):
        search_query = request.GET.get('q', '').strip()
        teachers = Teacher.objects.select_related('subject').prefetch_related('assigned_subjects', 'assigned_classes').all()
        if search_query:
            teachers = teachers.filter(
                Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        return render(request, 'teachers.html', {
            'teachers': teachers,
            'search_query': search_query,
            'form': TeacherForm(),
            'subjects': Subject.objects.all(),
            'classes': GradeClass.objects.all(),
        })


class TeacherCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def post(self, request):
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            messages.success(request, f"O'qituvchi {teacher.first_name} {teacher.last_name} muvaffaqiyatli qo'shildi!")
            return redirect('teacher_list')
        messages.error(request, "O'qituvchini qo'shishda xatolik!")
        return redirect('teacher_list')


class TeacherUpdateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def get(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)
        return render(request, 'teacher_form.html', {
            'teacher': teacher,
            'form': TeacherForm(instance=teacher),
        })

    def post(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, f"O'qituvchi {teacher.first_name} ma'lumotlari yangilandi!")
            return redirect('teacher_list')
        return render(request, 'teacher_form.html', {'teacher': teacher, 'form': form})


class TeacherDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def post(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)
        name = f"{teacher.first_name} {teacher.last_name}"
        teacher.delete()
        messages.success(request, f"O'qituvchi {name} o'chirildi.")
        return redirect('teacher_list')


# ── O'quvchilar Boshqaruvi ───────────────────────────────────

class StudentListView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def get(self, request):
        role = get_user_role(request.user)
        class_id = request.GET.get('class_id')
        search_query = request.GET.get('q', '').strip()

        students = Student.objects.select_related('grade_class').all()

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher:
                my_classes = teacher.assigned_classes.all()
                students = students.filter(grade_class__in=my_classes)

        if class_id:
            students = students.filter(grade_class_id=class_id)
        if search_query:
            students = students.filter(
                Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query) |
                Q(student_id__icontains=search_query) | Q(phone__icontains=search_query)
            )

        page_obj = Paginator(students, 15).get_page(request.GET.get('page'))
        return render(request, 'students.html', {
            'page_obj': page_obj,
            'students': page_obj.object_list,
            'classes': GradeClass.objects.all(),
            'selected_class': class_id,
            'search_query': search_query,
        })


class StudentProfileView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER, Role.STUDENT]

    def get(self, request, pk):
        student = get_object_or_404(Student.objects.select_related('grade_class'), pk=pk)
        role = get_user_role(request.user)

        # IDOR and Teacher workspace protection
        if role == Role.STUDENT and getattr(request.user, 'student_profile', None) != student:
            raise PermissionDenied("Boshqa o'quvchi profilini ko'rish taqiqlangan.")

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher or not teacher.assigned_classes.filter(pk=student.grade_class_id).exists():
                # Check if timetable has teacher
                if not Timetable.objects.filter(teacher=teacher, grade_class=student.grade_class).exists():
                    raise PermissionDenied("Boshqa o'qituvchining o'quvchisini ko'rish taqiqlangan.")

        attendances = Attendance.objects.filter(student=student).select_related('subject')[:15]
        grades = Grade.objects.filter(student=student).select_related('subject', 'teacher', 'lesson')[:15]
        total_att = attendances.count()
        present_att = attendances.filter(status='B').count()

        return render(request, 'student_profile.html', {
            'student': student,
            'grades': grades,
            'attendances': attendances,
            'fees': StudentFee.objects.filter(student=student).select_related('fee_type'),
            'submissions': HomeworkSubmission.objects.filter(student=student).select_related('homework__subject'),
            'att_percentage': round(present_att / total_att * 100, 1) if total_att > 0 else 100.0,
        })


class StudentCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def get(self, request):
        return render(request, 'student_form.html', {'form': StudentForm()})

    def post(self, request):
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"O'quvchi {student.first_name} {student.last_name} qo'shildi!")
            return redirect('student_profile', pk=student.pk)
        return render(request, 'student_form.html', {'form': form})


class StudentUpdateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_form.html', {'form': StudentForm(instance=student), 'student': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "O'quvchi ma'lumotlari yangilandi!")
            return redirect('student_profile', pk=student.pk)
        return render(request, 'student_form.html', {'form': form, 'student': student})


class StudentDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def get(self, request, pk):
        return render(request, 'student_delete.html', {'student': get_object_or_404(Student, pk=pk)})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"O'quvchi {name} o'chirildi.")
        return redirect('student_list')


# ── Darslar Boshqaruvi (Lesson Management) ───────────────────

class LessonListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        if role == Role.ADMIN:
            lessons = Lesson.objects.select_related('subject', 'teacher', 'grade_class').all()
        elif role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            lessons = Lesson.objects.filter(teacher=teacher).select_related('subject', 'teacher', 'grade_class') if teacher else Lesson.objects.none()
        else: # STUDENT
            student = getattr(request.user, 'student_profile', None)
            lessons = Lesson.objects.filter(grade_class=student.grade_class).select_related('subject', 'teacher', 'grade_class') if (student and student.grade_class) else Lesson.objects.none()

        return render(request, 'lessons.html', {
            'lessons': lessons,
            'form': LessonForm(),
            'subjects': Subject.objects.all(),
            'classes': GradeClass.objects.all(),
            'teachers': Teacher.objects.all(),
        })


class LessonCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def post(self, request):
        role = get_user_role(request.user)
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            if role == Role.TEACHER:
                teacher = getattr(request.user, 'teacher_profile', None)
                if not teacher:
                    raise PermissionDenied("O'qituvchi profili biriktirilmagan.")
                lesson.teacher = teacher

            try:
                lesson.full_clean()
                lesson.save()
                messages.success(request, f"Dars '{lesson.title}' saqlandi!")
            except ValidationError as e:
                messages.error(request, f"Xatolik: {e.messages[0]}")
            return redirect('lesson_list')
        messages.error(request, "Dars yaratishda formada xatolik yuz berdi!")
        return redirect('lesson_list')


class LessonUpdateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def get(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        role = get_user_role(request.user)
        if role == Role.TEACHER and lesson.teacher != getattr(request.user, 'teacher_profile', None):
            raise PermissionDenied("Boshqa o'qituvchining darsini tahrirlash taqiqlangan!")
        return render(request, 'lesson_form.html', {'form': LessonForm(instance=lesson), 'lesson': lesson})

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        role = get_user_role(request.user)
        if role == Role.TEACHER and lesson.teacher != getattr(request.user, 'teacher_profile', None):
            raise PermissionDenied("Boshqa o'qituvchining darsini tahrirlash taqiqlangan!")
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            try:
                updated_lesson = form.save(commit=False)
                updated_lesson.full_clean()
                updated_lesson.save()
                messages.success(request, "Dars muvaffaqiyatli yangilandi!")
                return redirect('lesson_list')
            except ValidationError as e:
                messages.error(request, f"Xatolik: {e.messages[0]}")
        return render(request, 'lesson_form.html', {'form': form, 'lesson': lesson})


class LessonDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        role = get_user_role(request.user)
        if role == Role.TEACHER and lesson.teacher != getattr(request.user, 'teacher_profile', None):
            raise PermissionDenied("Boshqa o'qituvchining darsini o'chirish taqiqlangan!")
        lesson.delete()
        messages.success(request, "Dars o'chirildi.")
        return redirect('lesson_list')


# ── Baholar Jurnali va Baholash (GradeBook & Evaluation) ──────

class GradeBookView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')

        classes = GradeClass.objects.all()
        subjects = Subject.objects.all()
        students, grades_matrix = [], {}

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher:
                classes = teacher.assigned_classes.all()
                subjects = (Subject.objects.filter(pk=teacher.subject_id) if teacher.subject else Subject.objects.none()) | teacher.assigned_subjects.all()
                subjects = subjects.distinct()

        elif role == Role.STUDENT:
            student = getattr(request.user, 'student_profile', None)
            if student:
                grades = Grade.objects.filter(student=student).select_related('subject', 'teacher', 'lesson')
                return render(request, 'grades.html', {
                    'student_mode': True,
                    'student': student,
                    'grades': grades,
                })

        if selected_class_id:
            students = Student.objects.filter(grade_class_id=selected_class_id).select_related('grade_class')
            grades_qs = Grade.objects.filter(student__in=students).select_related('subject', 'student', 'teacher', 'lesson')
            if selected_subject_id:
                grades_qs = grades_qs.filter(subject_id=selected_subject_id)
            if role == Role.TEACHER:
                teacher = getattr(request.user, 'teacher_profile', None)
                grades_qs = grades_qs.filter(teacher=teacher)
            for g in grades_qs:
                grades_matrix.setdefault(g.student_id, []).append(g)

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
        role = get_user_role(request.user)
        if role not in [Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Baho qo'yish ruxsati yo'q.")

        student_id = request.POST.get('student')
        subject_id = request.POST.get('subject')
        lesson_id = request.POST.get('lesson')

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher:
                raise PermissionDenied("O'qituvchi profili topilmadi.")

            student = Student.objects.filter(pk=student_id).first() if student_id else None
            subject = Subject.objects.filter(pk=subject_id).first() if subject_id else None

            # Strictly verify teacher assignment before form processing
            if not student or not subject or not teacher.is_assigned_to_subject_and_class(subject, student.grade_class):
                raise PermissionDenied("Boshqa o'qituvchining fani yoki sinfiga baho qo'yish taqiqlangan!")

            if lesson_id:
                lesson = Lesson.objects.filter(pk=lesson_id).first()
                if not lesson or lesson.teacher_id != teacher.id or lesson.subject_id != subject.id:
                    raise PermissionDenied("Boshqa o'qituvchining darsiga baho qo'yish taqiqlangan!")

        form = GradeForm(request.POST)
        if form.is_valid():
            grade = form.save(commit=False)
            if role == Role.TEACHER:
                grade.teacher = request.user.teacher_profile
            elif role == Role.ADMIN:
                if not grade.teacher_id:
                    teacher = Teacher.objects.filter(subject=grade.subject, assigned_classes=grade.student.grade_class).first() or Teacher.objects.filter(subject=grade.subject).first()
                    if teacher:
                        grade.teacher = teacher

            try:
                grade.full_clean()
                grade.save()
                messages.success(request, f"{grade.student.first_name}ga {grade.score} baho qo'yildi!")
                if grade.student.user:
                    send_system_notification(
                        grade.student.user, "Yangi Baho!",
                        f"{grade.subject.name} fanidan {grade.score} ball olindingiz.",
                        'EXAM', '/grades/'
                    )
            except ValidationError as e:
                messages.error(request, f"Xatolik: {e.messages[0] if hasattr(e, 'messages') else e}")
            return redirect(f'/grades/?class_id={grade.student.grade_class_id}&subject_id={grade.subject.id}')
        
        messages.error(request, "Baho kiritishda formada xatolik yuz berdi!")
        return redirect('gradebook')


# ── Yo'qlama / Davomat ────────────────────────────────────────

class AttendanceView(LoginRequiredMixin, View):
    def get(self, request):
        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')
        selected_date = request.GET.get('date', datetime.date.today().isoformat())
        students, existing_status = [], {}

        role = get_user_role(request.user)
        classes = GradeClass.objects.all()
        subjects = Subject.objects.all()

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher:
                classes = teacher.assigned_classes.all()
                subjects = (Subject.objects.filter(pk=teacher.subject_id) if teacher.subject else Subject.objects.none()) | teacher.assigned_subjects.all()
                subjects = subjects.distinct()

        if selected_class_id and selected_subject_id:
            students = Student.objects.filter(grade_class_id=selected_class_id)
            attendances = Attendance.objects.filter(
                subject_id=selected_subject_id, date=selected_date, student__in=students
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
        role = get_user_role(request.user)
        if role not in [Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Yo'qlama qilish ruxsati yo'q.")
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')
        date_str = request.POST.get('date')

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            subject = get_object_or_404(Subject, pk=subject_id)
            grade_class = get_object_or_404(GradeClass, pk=class_id)
            if not teacher or not teacher.is_assigned_to_subject_and_class(subject, grade_class):
                raise PermissionDenied("Boshqa o'qituvchining sinfi yoki faniga yo'qlama qilish taqiqlangan!")

        if class_id and subject_id and date_str:
            subject = get_object_or_404(Subject, pk=subject_id)
            for s in Student.objects.filter(grade_class_id=class_id):
                Attendance.objects.update_or_create(
                    student=s, subject=subject, date=date_str,
                    defaults={'status': request.POST.get(f'status_{s.id}', 'B')}
                )
            messages.success(request, "Davomat muvaffaqiyatli saqlandi!")
        return redirect(f'/attendance/?class_id={class_id}&subject_id={subject_id}&date={date_str}')


# ── Dars Jadvali ──────────────────────────────────────────────

class TimetableView(LoginRequiredMixin, View):
    def get(self, request):
        classes = GradeClass.objects.all()
        role = get_user_role(request.user)

        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher:
                classes = teacher.assigned_classes.all()
        elif role == Role.STUDENT:
            student = getattr(request.user, 'student_profile', None)
            if student and student.grade_class:
                classes = GradeClass.objects.filter(pk=student.grade_class.pk)

        selected_class_id = request.GET.get('class_id', classes.first().id if classes.exists() else None)
        schedule_by_day = {}
        if selected_class_id:
            for day_num, day_name in Timetable.DAYS:
                schedule_by_day[day_name] = Timetable.objects.filter(
                    grade_class_id=selected_class_id, day_of_week=day_num
                ).select_related('subject', 'teacher')
        return render(request, 'timetable.html', {
            'classes': classes,
            'selected_class_id': int(selected_class_id) if selected_class_id else None,
            'schedule_by_day': schedule_by_day,
            'form': TimetableForm(),
        })

    def post(self, request):
        if get_user_role(request.user) != Role.ADMIN:
            raise PermissionDenied("Dars jadvalini o'zgartirish ruxsati faqat Adminga berilgan.")
        form = TimetableForm(request.POST)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.full_clean()
                obj.save()
                messages.success(request, "Dars jadvaliga dars qo'shildi!")
            except ValidationError as e:
                messages.error(request, e.messages[0] if hasattr(e, 'messages') else "Konflikt yuz berdi!")
        else:
            messages.error(request, "Formada xatoliklar mavjud!")
        return redirect('timetable')


# ── Fanlar va Sinflar Boshqaruvi (Admin uchun) ────────────────

class SubjectListView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def get(self, request):
        return render(request, 'subjects.html', {
            'subjects': Subject.objects.all(),
            'form': SubjectForm(),
        })

    def post(self, request):
        if get_user_role(request.user) != Role.ADMIN:
            raise PermissionDenied("Fan qo'shish faqat Admin uchun.")
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Yangi fan qo'shildi!")
            return redirect('subject_list')
        messages.error(request, "Fan kiritishda xatolik!")
        return redirect('subject_list')


# ── To'lovlar (Fees & Payments) ───────────────────────────────

class FeeListView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.STUDENT]

    def get(self, request):
        role = get_user_role(request.user)
        if role == Role.STUDENT:
            fees = StudentFee.objects.filter(student=getattr(request.user, 'student_profile', None)).select_related('fee_type', 'student')
        else:
            fees = StudentFee.objects.select_related('fee_type', 'student__grade_class').all()

        status_filter = request.GET.get('status')
        if status_filter:
            fees = fees.filter(status=status_filter)

        return render(request, 'fees.html', {
            'fees': fees,
            'fee_types': FeeType.objects.all(),
            'fee_form': StudentFeeForm(),
            'payment_form': PaymentRecordForm(),
        })


class StudentFeeCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def post(self, request):
        form = StudentFeeForm(request.POST)
        if form.is_valid():
            fee = form.save()
            messages.success(request, f"{fee.student} uchun {fee.fee_type.name} biriktirildi!")
            if fee.student.user:
                send_system_notification(
                    fee.student.user, "Yangi To'lov Belgilandi",
                    f"{fee.fee_type.name}: {fee.net_amount:,.0f} UZS to'lovi biriktirildi.",
                    'FEE', '/fees/'
                )
        else:
            messages.error(request, "To'lov biriktirishda xatolik yuz berdi.")
        return redirect('fee_list')


class PaymentRecordCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN]

    def post(self, request, fee_id):
        fee = get_object_or_404(StudentFee, pk=fee_id)
        form = PaymentRecordForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student_fee = fee
            payment.save()
            messages.success(request, f"To'lov qabul qilindi! Chek #{payment.receipt_number}")
        else:
            messages.error(request, "To'lovni saqlashda xatolik yuz berdi.")
        return redirect('fee_list')


class InvoicePrintView(LoginRequiredMixin, View):
    def get(self, request, fee_id):
        fee = get_object_or_404(StudentFee.objects.select_related('student__grade_class', 'fee_type'), pk=fee_id)
        return render(request, 'invoice.html', {'fee': fee, 'payments': fee.payments.all()})


# ── Uyga Vazifalar (Homework) ─────────────────────────────────

class HomeworkListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        if role == Role.STUDENT:
            student = getattr(request.user, 'student_profile', None)
            homeworks = Homework.objects.filter(grade_class=student.grade_class).select_related('grade_class', 'subject') if (student and student.grade_class) else Homework.objects.none()
        elif role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            homeworks = Homework.objects.filter(teacher=teacher).select_related('grade_class', 'subject', 'teacher') if teacher else Homework.objects.none()
        else:
            homeworks = Homework.objects.select_related('grade_class', 'subject', 'teacher').all()

        return render(request, 'homework.html', {'homeworks': homeworks, 'form': HomeworkForm()})

    def post(self, request):
        role = get_user_role(request.user)
        if role not in [Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Vazifa yaratish ruxsati yo'q.")
        form = HomeworkForm(request.POST, request.FILES)
        if form.is_valid():
            hw = form.save(commit=False)
            if role == Role.TEACHER:
                teacher = getattr(request.user, 'teacher_profile', None)
                if not teacher or not teacher.is_assigned_to_subject_and_class(hw.subject, hw.grade_class):
                    raise PermissionDenied("Boshqa o'qituvchining fani yoki sinfiga vazifa yaratish taqiqlangan!")
                hw.teacher = teacher
            hw.save()
            messages.success(request, "Yangi uyga vazifa e'lon qilindi!")
            return redirect('homework_list')
        messages.error(request, "Vazifa kiritishda xatolik!")
        return redirect('homework_list')


class HomeworkSubmitView(RoleRequiredMixin, View):
    allowed_roles = [Role.STUDENT]

    def post(self, request, homework_id):
        hw = get_object_or_404(Homework, pk=homework_id)
        student = getattr(request.user, 'student_profile', None)
        if not student:
            messages.error(request, "O'quvchi profili topilmadi.")
            return redirect('homework_list')
        form = HomeworkSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            HomeworkSubmission.objects.update_or_create(
                homework=hw, student=student,
                defaults={
                    'submission_text': form.cleaned_data['submission_text'],
                    'attachment': form.cleaned_data.get('attachment') or None,
                    'status': 'SUBMITTED'
                }
            )
            messages.success(request, "Vazifa topshirildi!")
        else:
            messages.error(request, "Topshirishda xatolik yuz berdi.")
        return redirect('homework_list')


# ── Imtihonlar ────────────────────────────────────────────────

class ExamListView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'exams.html', {
            'exams': Exam.objects.select_related('subject', 'grade_class').all(),
            'form': ExamForm(),
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Imtihon yaratish ruxsati yo'q.")
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f"Imtihon {exam.title} yaratildi!")
            return redirect('exam_list')
        messages.error(request, "Formada xatolik yuz berdi.")
        return redirect('exam_list')


class ExamResultEntryView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.select_related('grade_class', 'subject'), pk=exam_id)
        role = get_user_role(request.user)
        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher or not teacher.is_assigned_to_subject_and_class(exam.subject, exam.grade_class):
                raise PermissionDenied("Boshqa o'qituvchining imtihoniga kirish taqiqlangan!")
        return render(request, 'exam_results_entry.html', {
            'exam': exam,
            'students': Student.objects.filter(grade_class=exam.grade_class),
            'existing_results': {r.student_id: r for r in ExamResult.objects.filter(exam=exam)},
        })

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        role = get_user_role(request.user)
        if role == Role.TEACHER:
            teacher = getattr(request.user, 'teacher_profile', None)
            if not teacher or not teacher.is_assigned_to_subject_and_class(exam.subject, exam.grade_class):
                raise PermissionDenied("Boshqa o'qituvchining imtihonini tahrirlash taqiqlangan!")
        for st in Student.objects.filter(grade_class=exam.grade_class):
            mark_val = request.POST.get(f'mark_{st.id}')
            if mark_val:
                try:
                    ExamResult.objects.update_or_create(
                        exam=exam, student=st,
                        defaults={'marks_obtained': float(mark_val), 'teacher_comments': request.POST.get(f'comment_{st.id}', '')}
                    )
                except ValueError:
                    pass
        for rank, result in enumerate(ExamResult.objects.filter(exam=exam).order_by('-percentage'), 1):
            result.rank = rank
            result.save()
        messages.success(request, "Imtihon natijalari saqlandi!")
        return redirect('exam_list')


# ── E'lonlar va Xabarnomalar ──────────────────────────────────

class AnnouncementListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        return render(request, 'announcements.html', {
            'announcements': Announcement.objects.select_related('created_by', 'grade_class').filter(
                Q(target_role='ALL') |
                (Q(target_role='TEACHERS') if role == Role.TEACHER else Q()) |
                (Q(target_role='STUDENTS') if role == Role.STUDENT else Q())
            ),
            'form': AnnouncementForm(),
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("E'lon berish ruxsati yo'q.")
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            anc = form.save(commit=False)
            anc.created_by = request.user
            anc.save()
            messages.success(request, "E'lon e'lon qilindi!")
            return redirect('announcement_list')
        messages.error(request, "E'lon kiritishda xatolik!")
        return redirect('announcement_list')


class NotificationListView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'notifications.html', {
            'notifications': Notification.objects.filter(user=request.user)
        })


class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})


# ── Quizzes ───────────────────────────────────────────────────

class QuizListView(LoginRequiredMixin, View):
    def get(self, request):
        quizzes = Quiz.objects.select_related('subject').annotate(num_questions=Count('questions')).all()
        return render(request, 'quizzes.html', {'quizzes': quizzes})


class QuizTakeView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        return render(request, 'quiz_take.html', {'quiz': quiz, 'questions': quiz.questions.all()})

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        questions = quiz.questions.all()

        student = getattr(request.user, 'student_profile', None) or Student.objects.filter(user=request.user).first()
        if not student:
            messages.error(request, "Test topshirish uchun O'quvchi profili zarur!")
            return redirect('quiz_list')

        correct = sum(1 for q in questions if request.POST.get(f'q_{q.id}') == q.correct_option)
        total = questions.count()
        result = QuizResult.objects.create(
            student=student, quiz=quiz, score=correct, total_questions=total,
            percentage=round(correct / total * 100, 1) if total > 0 else 0
        )
        return render(request, 'quiz_result.html', {'result': result, 'quiz': quiz})


# ── Export (CSV) ──────────────────────────────────────────────

class ExportDataView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.TEACHER]

    def get(self, request, model_type):
        role = get_user_role(request.user)
        if model_type == 'students':
            students = Student.objects.select_related('grade_class').all()
            if role == Role.TEACHER:
                teacher = getattr(request.user, 'teacher_profile', None)
                if teacher:
                    students = students.filter(grade_class__in=teacher.assigned_classes.all())
                else:
                    students = Student.objects.none()
            return export_queryset_to_csv(
                students,
                ['student_id', 'first_name', 'last_name', 'grade_class__name', 'phone', 'status'],
                ['ID Kodi', 'Ismi', 'Familiyasi', 'Sinfi', 'Telefoni', 'Holati'],
                'oquvchilar_ruyxati.csv'
            )
        if model_type == 'fees' and role == Role.ADMIN:
            return export_queryset_to_csv(
                StudentFee.objects.select_related('student', 'fee_type').all(),
                ['student__student_id', 'student__first_name', 'student__last_name', 'fee_type__name', 'amount', 'status', 'due_date'],
                ["O'quvchi ID", 'Ismi', 'Familiyasi', "To'lov Turi", 'Summa', 'Holati', 'Muddati'],
                'tolovlar_ruyxati.csv'
            )
        if model_type == 'attendance':
            attendances = Attendance.objects.select_related('student', 'subject').all()
            if role == Role.TEACHER:
                teacher = getattr(request.user, 'teacher_profile', None)
                if teacher:
                    attendances = attendances.filter(student__grade_class__in=teacher.assigned_classes.all())
                else:
                    attendances = Attendance.objects.none()
            return export_queryset_to_csv(
                attendances[:500],
                ['date', 'student__first_name', 'student__last_name', 'subject__name', 'status'],
                ['Sana', 'Ismi', 'Familiyasi', 'Fan', 'Holati'],
                'davomat_yozuvlari.csv'
            )
        messages.error(request, "Eksport modeli topilmadi.")
        return redirect('home')


# ── Error Handlers ────────────────────────────────────────────

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_403(request, exception=None):
    return render(request, '403.html', status=403)

def custom_500(request):
    return render(request, '500.html', status=500)