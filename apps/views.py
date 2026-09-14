import datetime
import logging
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib import messages

from .models import (
    UserProfile, GradeClass, Subject, ParentProfile, Teacher, Student,
    Timetable, Grade, Attendance, FeeType, StudentFee, PaymentRecord,
    Homework, HomeworkSubmission, Exam, ExamResult, Announcement,
    Notification, Quiz, Question, QuizResult
)
from .forms import (
    StudentForm, ParentProfileForm, SubjectForm, GradeClassForm, TimetableForm,
    HomeworkForm, HomeworkSubmissionForm, GradeForm, FeeTypeForm, StudentFeeForm,
    PaymentRecordForm, ExamForm, AnnouncementForm, RegisterForm
)
from .permissions import Role, RoleRequiredMixin, get_user_role, role_required
from .utils import send_system_notification, export_queryset_to_csv

logger = logging.getLogger('apps')


# ──────────────────────────────────────────────────────────────
# Authentication Views
# ──────────────────────────────────────────────────────────────

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
            logger.info(f"User login successful: {username}")
            return redirect('home')
        logger.warning(f"User login failed: {username}")
        return render(request, 'login.html', {'error': 'Username yoki parol noto\'g\'ri!'})


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
                Student.objects.create(
                    user=user,
                    first_name=user.first_name or user.username,
                    last_name=user.last_name or '',
                    email=user.email
                )
            elif role == Role.TEACHER:
                Teacher.objects.create(
                    user=user,
                    first_name=user.first_name or user.username,
                    last_name=user.last_name or '',
                    phone=''
                )

            login(request, user)
            messages.success(request, "Akkauntingiz muvaffaqiyatli yaratildi!")
            return redirect('home')
        return render(request, 'register.html', {'form': form})


# ──────────────────────────────────────────────────────────────
# Role-Based Dashboard / Home View
# ──────────────────────────────────────────────────────────────

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        role = get_user_role(user)

        context = {
            'today_date': datetime.date.today(),
            'announcements': Announcement.objects.select_related('created_by').filter(
                Q(target_role='ALL') | Q(target_role=role)
            )[:5],
        }

        # Parent Dashboard
        if role == Role.PARENT:
            parent_profile = getattr(user, 'parent_profile', None)
            children = parent_profile.children.all() if parent_profile else Student.objects.none()
            selected_child_id = request.GET.get('child_id')
            selected_child = children.filter(pk=selected_child_id).first() if selected_child_id else children.first()

            child_attendance = Attendance.objects.filter(student=selected_child)[:10] if selected_child else []
            child_grades = Grade.objects.filter(student=selected_child).select_related('subject')[:10] if selected_child else []
            child_fees = StudentFee.objects.filter(student=selected_child).select_related('fee_type') if selected_child else []
            child_homeworks = Homework.objects.filter(grade_class=selected_child.grade_class)[:5] if (selected_child and selected_child.grade_class) else []

            context.update({
                'children': children,
                'selected_child': selected_child,
                'child_attendance': child_attendance,
                'child_grades': child_grades,
                'child_fees': child_fees,
                'child_homeworks': child_homeworks,
            })
            return render(request, 'parent_dashboard.html', context)

        # Student Dashboard
        if role == Role.STUDENT:
            student = getattr(user, 'student_profile', None)
            if not student:
                student = Student.objects.filter(user=user).first()

            student_grades = Grade.objects.filter(student=student).select_related('subject')[:8] if student else []
            student_attendances = Attendance.objects.filter(student=student).select_related('subject')[:5] if student else []
            student_fees = StudentFee.objects.filter(student=student).select_related('fee_type') if student else []
            student_homeworks = Homework.objects.filter(grade_class=student.grade_class)[:5] if (student and student.grade_class) else []

            context.update({
                'student': student,
                'student_grades': student_grades,
                'student_attendances': student_attendances,
                'student_fees': student_fees,
                'student_homeworks': student_homeworks,
            })
            return render(request, 'home.html', context)

        # Teacher & Admin Dashboard
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_classes = GradeClass.objects.count()
        total_subjects = Subject.objects.count()
        total_quizzes = Quiz.objects.count()

        today_num = datetime.date.today().isoweekday()
        today_timetables = Timetable.objects.filter(day_of_week=today_num).select_related('grade_class', 'subject', 'teacher')[:6]
        recent_grades = Grade.objects.select_related('student', 'subject').all()[:6]
        top_students = Student.objects.annotate(avg_score=Avg('quiz_results__percentage')).filter(avg_score__isnull=False).order_by('-avg_score')[:5]

        # Financial metrics for Accountant/Admin
        pending_fees_total = StudentFee.objects.filter(status__in=['PENDING', 'OVERDUE', 'PARTIAL']).aggregate(total=Sum('amount'))['total'] or 0
        monthly_revenue = PaymentRecord.objects.filter(payment_date__month=datetime.date.today().month).aggregate(total=Sum('paid_amount'))['total'] or 0

        context.update({
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_classes': total_classes,
            'total_subjects': total_subjects,
            'total_quizzes': total_quizzes,
            'recent_grades': recent_grades,
            'today_timetables': today_timetables,
            'top_students': top_students,
            'pending_fees_total': pending_fees_total,
            'monthly_revenue': monthly_revenue,
        })
        return render(request, 'home.html', context)


# ──────────────────────────────────────────────────────────────
# Student Management
# ──────────────────────────────────────────────────────────────

class StudentListView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER, Role.RECEPTIONIST, Role.ACCOUNTANT]

    def get(self, request):
        class_id = request.GET.get('class_id')
        search_query = request.GET.get('q', '').strip()

        students = Student.objects.select_related('grade_class', 'parent').all()
        if class_id:
            students = students.filter(grade_class_id=class_id)
        if search_query:
            students = students.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(student_id__icontains=search_query) |
                Q(phone__icontains=search_query)
            )

        paginator = Paginator(students, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        classes = GradeClass.objects.all()
        return render(request, 'students.html', {
            'page_obj': page_obj,
            'students': page_obj.object_list,
            'classes': classes,
            'selected_class': class_id,
            'search_query': search_query,
        })


class StudentProfileView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER, Role.RECEPTIONIST, Role.ACCOUNTANT, Role.STUDENT, Role.PARENT]

    def get(self, request, pk):
        student = get_object_or_404(Student.objects.select_related('grade_class', 'parent'), pk=pk)

        # IDOR Protection: Student/Parent can only view own profile
        role = get_user_role(request.user)
        if role == Role.STUDENT and (not hasattr(request.user, 'student_profile') or request.user.student_profile.pk != student.pk):
            raise PermissionDenied("Boshqa o'quvchi profilini ko'rish taqiqlangan.")
        if role == Role.PARENT and (not hasattr(request.user, 'parent_profile') or student.parent != request.user.parent_profile):
            raise PermissionDenied("Boshqa o'quvchi profilini ko'rish taqiqlangan.")

        grades = Grade.objects.filter(student=student).select_related('subject')[:15]
        attendances = Attendance.objects.filter(student=student).select_related('subject')[:15]
        fees = StudentFee.objects.filter(student=student).select_related('fee_type')
        submissions = HomeworkSubmission.objects.filter(student=student).select_related('homework__subject')

        # Attendance calculation
        total_att = attendances.count()
        present_att = attendances.filter(status='B').count()
        att_percentage = round((present_att / total_att * 100), 1) if total_att > 0 else 100.0

        return render(request, 'student_profile.html', {
            'student': student,
            'grades': grades,
            'attendances': attendances,
            'fees': fees,
            'submissions': submissions,
            'att_percentage': att_percentage,
        })


class StudentCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.RECEPTIONIST]

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
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.RECEPTIONIST]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_form.html', {'form': StudentForm(instance=student), 'student': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"O'quvchi ma'lumotlari yangilandi!")
            return redirect('student_profile', pk=student.pk)
        return render(request, 'student_form.html', {'form': form, 'student': student})


class StudentDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        return render(request, 'student_delete.html', {'student': student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"O'quvchi {name} o'chirildi.")
        return redirect('student_list')


# ──────────────────────────────────────────────────────────────
# Parent Management
# ──────────────────────────────────────────────────────────────

class ParentDashboardView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.PARENT]

    def get(self, request):
        user = request.user
        parent = getattr(user, 'parent_profile', None)
        children = parent.children.all() if parent else Student.objects.none()

        selected_id = request.GET.get('child_id')
        selected_child = children.filter(pk=selected_id).first() if selected_id else children.first()

        attendances = Attendance.objects.filter(student=selected_child).select_related('subject')[:10] if selected_child else []
        grades = Grade.objects.filter(student=selected_child).select_related('subject')[:10] if selected_child else []
        fees = StudentFee.objects.filter(student=selected_child).select_related('fee_type') if selected_child else []
        homeworks = Homework.objects.filter(grade_class=selected_child.grade_class)[:5] if (selected_child and selected_child.grade_class) else []

        return render(request, 'parent_dashboard.html', {
            'children': children,
            'selected_child': selected_child,
            'child_attendance': attendances,
            'child_grades': grades,
            'child_fees': fees,
            'child_homeworks': homeworks,
        })


# ──────────────────────────────────────────────────────────────
# Grade Book Journal
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
            students = Student.objects.filter(grade_class_id=selected_class_id).select_related('grade_class')
            grades_qs = Grade.objects.filter(student__in=students).select_related('subject', 'student')
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
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Baho qo'yish ruxsati yo'q.")

        form = GradeForm(request.POST)
        if form.is_valid():
            grade = form.save()
            messages.success(request, f"{grade.student.first_name}ga {grade.score} baho qo'yildi!")
            
            # Send notification to student user
            if grade.student.user:
                send_system_notification(
                    user=grade.student.user,
                    title="Yangi Baho!",
                    message=f"{grade.subject.name} fanidan {grade.score} ball olindingiz.",
                    notification_type='EXAM',
                    link='/grades/'
                )
            
            c_id = grade.student.grade_class_id
            s_id = grade.subject.id
            return redirect(f'/grades/?class_id={c_id}&subject_id={s_id}')

        messages.error(request, "Baho kiritishda xatolik yuz berdi!")
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
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Yo'qlama qilish ruxsati yo'q.")

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
            messages.success(request, "Davomat muvaffaqiyatli saqlandi!")
        return redirect(f'/attendance/?class_id={class_id}&subject_id={subject_id}&date={date_str}')


# ──────────────────────────────────────────────────────────────
# Dars Jadvali & Timetable Conflict Check
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

        form = TimetableForm()
        return render(request, 'timetable.html', {
            'classes': classes,
            'selected_class_id': int(selected_class_id) if selected_class_id else None,
            'schedule_by_day': schedule_by_day,
            'form': form,
        })

    def post(self, request):
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN]:
            raise PermissionDenied("Dars jadvalini o'zgartirish ruxsati yo'q.")

        form = TimetableForm(request.POST)
        if form.is_valid():
            try:
                timetable_obj = form.save(commit=False)
                timetable_obj.full_clean()
                timetable_obj.save()
                messages.success(request, "Dars jadvaliga dars qo'shildi!")
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else "Konflikt yuz berdi!")
        else:
            messages.error(request, "Formada xatoliklar mavjud!")
        return redirect('timetable')


# ──────────────────────────────────────────────────────────────
# Fees & Payment Management
# ──────────────────────────────────────────────────────────────

class FeeListView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT, Role.STUDENT, Role.PARENT]

    def get(self, request):
        user = request.user
        role = get_user_role(user)

        if role == Role.STUDENT:
            student = getattr(user, 'student_profile', None)
            fees = StudentFee.objects.filter(student=student).select_related('fee_type', 'student')
        elif role == Role.PARENT:
            parent = getattr(user, 'parent_profile', None)
            children = parent.children.all() if parent else []
            fees = StudentFee.objects.filter(student__in=children).select_related('fee_type', 'student')
        else:
            fees = StudentFee.objects.select_related('fee_type', 'student__grade_class').all()

        status_filter = request.GET.get('status')
        if status_filter:
            fees = fees.filter(status=status_filter)

        fee_types = FeeType.objects.all()
        return render(request, 'fees.html', {
            'fees': fees,
            'fee_types': fee_types,
            'fee_form': StudentFeeForm(),
            'payment_form': PaymentRecordForm(),
        })


class StudentFeeCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT]

    def post(self, request):
        form = StudentFeeForm(request.POST)
        if form.is_valid():
            fee = form.save()
            messages.success(request, f"{fee.student} uchun {fee.fee_type.name} biriktirildi!")
            if fee.student.user:
                send_system_notification(
                    user=fee.student.user,
                    title="Yangi To'lov Belgilandi",
                    message=f"{fee.fee_type.name}: {fee.net_amount:,.0f} UZS to'lovi biriktirildi.",
                    notification_type='FEE',
                    link='/fees/'
                )
        else:
            messages.error(request, "To'lov biriktirishda xatolik yuz berdi.")
        return redirect('fee_list')


class PaymentRecordCreateView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT]

    def post(self, request, fee_id):
        fee = get_object_or_404(StudentFee, pk=fee_id)
        form = PaymentRecordForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student_fee = fee
            payment.save()
            messages.success(request, f"To'lov muvaffaqiyatli qabul qilindi! Chek #{payment.receipt_number}")
        else:
            messages.error(request, "To'lovni saqlashda xatolik yuz berdi.")
        return redirect('fee_list')


class InvoicePrintView(LoginRequiredMixin, View):
    def get(self, request, fee_id):
        fee = get_object_or_404(StudentFee.objects.select_related('student__grade_class', 'fee_type'), pk=fee_id)
        payments = fee.payments.all()
        return render(request, 'invoice.html', {
            'fee': fee,
            'payments': payments,
        })


# ──────────────────────────────────────────────────────────────
# Homework & Submissions
# ──────────────────────────────────────────────────────────────

class HomeworkListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        user = request.user

        if role == Role.STUDENT:
            student = getattr(user, 'student_profile', None)
            homeworks = Homework.objects.filter(grade_class=student.grade_class).select_related('grade_class', 'subject') if student else Homework.objects.none()
        else:
            homeworks = Homework.objects.select_related('grade_class', 'subject', 'teacher').all()

        form = HomeworkForm()
        return render(request, 'homework.html', {'homeworks': homeworks, 'form': form})

    def post(self, request):
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Vazifa yaratish ruxsati yo'q.")

        form = HomeworkForm(request.POST, request.FILES)
        if form.is_valid():
            hw = form.save()
            messages.success(request, "Yangi uyga vazifa e'lon qilindi!")
            # Notify students of class
            students = Student.objects.filter(grade_class=hw.grade_class)
            for st in students:
                if st.user:
                    send_system_notification(
                        user=st.user,
                        title=f"Yangi Uyga Vazifa: {hw.subject.name}",
                        message=f"{hw.title} (Muddat: {hw.due_date})",
                        notification_type='HOMEWORK',
                        link='/homework/'
                    )
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
            sub, created = HomeworkSubmission.objects.update_or_create(
                homework=hw, student=student,
                defaults={
                    'submission_text': form.cleaned_data['submission_text'],
                    'attachment': form.cleaned_data['attachment'] or None,
                    'status': 'SUBMITTED'
                }
            )
            messages.success(request, "Vazifa topshirildi!")
        else:
            messages.error(request, "Topshirishda xatolik yuz berdi.")
        return redirect('homework_list')


# ──────────────────────────────────────────────────────────────
# Exams & Results
# ──────────────────────────────────────────────────────────────

class ExamListView(LoginRequiredMixin, View):
    def get(self, request):
        exams = Exam.objects.select_related('subject', 'grade_class').all()
        form = ExamForm()
        return render(request, 'exams.html', {'exams': exams, 'form': form})

    def post(self, request):
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Imtihon yaratish ruxsati yo'q.")

        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f"Imtihon {exam.title} yaratildi!")
            return redirect('exam_list')
        messages.error(request, "Formada xatolik yuz berdi.")
        return redirect('exam_list')


class ExamResultEntryView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.select_related('grade_class', 'subject'), pk=exam_id)
        students = Student.objects.filter(grade_class=exam.grade_class)
        existing_results = {r.student_id: r for r in ExamResult.objects.filter(exam=exam)}

        return render(request, 'exam_results_entry.html', {
            'exam': exam,
            'students': students,
            'existing_results': existing_results,
        })

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
        students = Student.objects.filter(grade_class=exam.grade_class)

        for st in students:
            mark_val = request.POST.get(f'mark_{st.id}')
            comment = request.POST.get(f'comment_{st.id}', '')
            if mark_val is not None and mark_val != '':
                try:
                    marks = float(mark_val)
                    res, created = ExamResult.objects.update_or_create(
                        exam=exam, student=st,
                        defaults={
                            'marks_obtained': marks,
                            'teacher_comments': comment
                        }
                    )
                except ValueError:
                    pass

        # Calculate ranks
        results = list(ExamResult.objects.filter(exam=exam).order_by('-percentage'))
        for rank_idx, r in enumerate(results, 1):
            r.rank = rank_idx
            r.save()

        messages.success(request, "Imtihon natijalari saqlandi va darajalar hisoblandi!")
        return redirect('exam_list')


# ──────────────────────────────────────────────────────────────
# Announcements & Notifications
# ──────────────────────────────────────────────────────────────

class AnnouncementListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        announcements = Announcement.objects.select_related('created_by', 'grade_class').filter(
            Q(target_role='ALL') | Q(target_role=role)
        )
        return render(request, 'announcements.html', {
            'announcements': announcements,
            'form': AnnouncementForm(),
        })

    def post(self, request):
        role = get_user_role(request.user)
        if role not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
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
        notifications = Notification.objects.filter(user=request.user)
        return render(request, 'notifications.html', {'notifications': notifications})


class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})


# ──────────────────────────────────────────────────────────────
# Bilim.uz Quiz Platform
# ──────────────────────────────────────────────────────────────

class QuizListView(LoginRequiredMixin, View):
    def get(self, request):
        quizzes = Quiz.objects.select_related('subject').annotate(num_questions=Count('questions')).all()
        return render(request, 'quizzes.html', {'quizzes': quizzes})


class QuizTakeView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        questions = quiz.questions.all()
        return render(request, 'quiz_take.html', {
            'quiz': quiz,
            'questions': questions,
        })

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        questions = quiz.questions.all()

        # Secure student detection: current authenticated user's student profile
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student = Student.objects.filter(user=request.user).first()
        if not student:
            student_id = request.POST.get('student_id')
            if student_id and get_user_role(request.user) in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
                student = get_object_or_404(Student, pk=student_id)
            else:
                messages.error(request, "Test topshirish uchun O'quvchi profili biriktirilgan bo'lishi kerak!")
                return redirect('quiz_list')

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
        results = QuizResult.objects.select_related('student__grade_class', 'quiz').order_by('-percentage', '-score')[:25]
        return render(request, 'leaderboard.html', {'results': results})


# ──────────────────────────────────────────────────────────────
# Data Export (CSV)
# ──────────────────────────────────────────────────────────────

class ExportDataView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT, Role.TEACHER]

    def get(self, request, model_type):
        if model_type == 'students':
            qs = Student.objects.select_related('grade_class').all()
            fields = ['student_id', 'first_name', 'last_name', 'grade_class__name', 'phone', 'parent_phone', 'status']
            headers = ['ID Kodi', 'Ismi', 'Familiyasi', 'Sinfi', 'Telefoni', 'Ota-ona Telefoni', 'Holati']
            return export_queryset_to_csv(qs, fields, headers, 'oquvchilar_ruyxati.csv')

        elif model_type == 'fees':
            qs = StudentFee.objects.select_related('student', 'fee_type').all()
            fields = ['student__student_id', 'student__first_name', 'student__last_name', 'fee_type__name', 'amount', 'status', 'due_date']
            headers = ['O\'quvchi ID', 'Ismi', 'Familiyasi', 'To\'lov Turi', 'Summa', 'Holati', 'Muddati']
            return export_queryset_to_csv(qs, fields, headers, 'tolovlar_ruyxati.csv')

        elif model_type == 'attendance':
            qs = Attendance.objects.select_related('student', 'subject').all()[:500]
            fields = ['date', 'student__first_name', 'student__last_name', 'subject__name', 'status']
            headers = ['Sana', 'Ismi', 'Familiyasi', 'Fan', 'Holati']
            return export_queryset_to_csv(qs, fields, headers, 'davomat_yozuvlari.csv')

        messages.error(request, "Eksport modeli topilmadi.")
        return redirect('home')


# ──────────────────────────────────────────────────────────────
# Custom Error Handlers
# ──────────────────────────────────────────────────────────────

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_403(request, exception=None):
    return render(request, '403.html', status=403)

def custom_500(request):
    return render(request, '500.html', status=500)