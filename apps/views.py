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


# ── Authentication ────────────────────────────────────────────

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


# ── Dashboard ─────────────────────────────────────────────────

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        role = get_user_role(user)
        today = datetime.date.today()

        context = {
            'today_date': today,
            'announcements': Announcement.objects.select_related('created_by').filter(
                Q(target_role='ALL') | Q(target_role=role)
            )[:5],
        }

        if role == Role.PARENT:
            return redirect('parent_dashboard')

        if role == Role.STUDENT:
            student = getattr(user, 'student_profile', None) or Student.objects.filter(user=user).first()
            context.update({
                'student': student,
                'student_grades': Grade.objects.filter(student=student).select_related('subject')[:8] if student else [],
                'student_attendances': Attendance.objects.filter(student=student).select_related('subject')[:5] if student else [],
                'student_fees': StudentFee.objects.filter(student=student).select_related('fee_type') if student else [],
                'student_homeworks': Homework.objects.filter(grade_class=student.grade_class)[:5] if (student and student.grade_class) else [],
            })
            return render(request, 'home.html', context)

        # Admin / Teacher dashboard
        context.update({
            'total_students': Student.objects.count(),
            'total_teachers': Teacher.objects.count(),
            'total_classes': GradeClass.objects.count(),
            'total_subjects': Subject.objects.count(),
            'total_quizzes': Quiz.objects.count(),
            'today_timetables': Timetable.objects.filter(day_of_week=today.isoweekday()).select_related('grade_class', 'subject', 'teacher')[:6],
            'recent_grades': Grade.objects.select_related('student', 'subject').all()[:6],
            'top_students': Student.objects.annotate(avg_score=Avg('quiz_results__percentage')).filter(avg_score__isnull=False).order_by('-avg_score')[:5],
            'pending_fees_total': StudentFee.objects.filter(status__in=['PENDING', 'OVERDUE', 'PARTIAL']).aggregate(total=Sum('amount'))['total'] or 0,
            'monthly_revenue': PaymentRecord.objects.filter(payment_date__month=today.month).aggregate(total=Sum('paid_amount'))['total'] or 0,
        })
        return render(request, 'home.html', context)


# ── Students ──────────────────────────────────────────────────

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
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER, Role.RECEPTIONIST, Role.ACCOUNTANT, Role.STUDENT, Role.PARENT]

    def get(self, request, pk):
        student = get_object_or_404(Student.objects.select_related('grade_class', 'parent'), pk=pk)
        role = get_user_role(request.user)

        # IDOR Protection
        if role == Role.STUDENT and getattr(request.user, 'student_profile', None) != student:
            raise PermissionDenied("Boshqa o'quvchi profilini ko'rish taqiqlangan.")
        if role == Role.PARENT and student.parent != getattr(request.user, 'parent_profile', None):
            raise PermissionDenied("Boshqa o'quvchi profilini ko'rish taqiqlangan.")

        attendances = Attendance.objects.filter(student=student).select_related('subject')[:15]
        total_att = attendances.count()
        present_att = attendances.filter(status='B').count()

        return render(request, 'student_profile.html', {
            'student': student,
            'grades': Grade.objects.filter(student=student).select_related('subject')[:15],
            'attendances': attendances,
            'fees': StudentFee.objects.filter(student=student).select_related('fee_type'),
            'submissions': HomeworkSubmission.objects.filter(student=student).select_related('homework__subject'),
            'att_percentage': round(present_att / total_att * 100, 1) if total_att > 0 else 100.0,
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
            messages.success(request, "O'quvchi ma'lumotlari yangilandi!")
            return redirect('student_profile', pk=student.pk)
        return render(request, 'student_form.html', {'form': form, 'student': student})


class StudentDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN]

    def get(self, request, pk):
        return render(request, 'student_delete.html', {'student': get_object_or_404(Student, pk=pk)})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"O'quvchi {name} o'chirildi.")
        return redirect('student_list')


# ── Parent Dashboard ──────────────────────────────────────────

class ParentDashboardView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.PARENT]

    def get(self, request):
        parent = getattr(request.user, 'parent_profile', None)
        children = parent.children.all() if parent else Student.objects.none()
        selected_id = request.GET.get('child_id')
        child = children.filter(pk=selected_id).first() if selected_id else children.first()

        return render(request, 'parent_dashboard.html', {
            'children': children,
            'selected_child': child,
            'child_attendance': Attendance.objects.filter(student=child).select_related('subject')[:10] if child else [],
            'child_grades': Grade.objects.filter(student=child).select_related('subject')[:10] if child else [],
            'child_fees': StudentFee.objects.filter(student=child).select_related('fee_type') if child else [],
            'child_homeworks': Homework.objects.filter(grade_class=child.grade_class)[:5] if (child and child.grade_class) else [],
        })


# ── Grade Book ────────────────────────────────────────────────

class GradeBookView(LoginRequiredMixin, View):
    def get(self, request):
        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')
        students, grades_matrix = [], {}

        if selected_class_id:
            students = Student.objects.filter(grade_class_id=selected_class_id).select_related('grade_class')
            grades_qs = Grade.objects.filter(student__in=students).select_related('subject', 'student')
            if selected_subject_id:
                grades_qs = grades_qs.filter(subject_id=selected_subject_id)
            for g in grades_qs:
                grades_matrix.setdefault(g.student_id, []).append(g)

        return render(request, 'grades.html', {
            'classes': GradeClass.objects.all(),
            'subjects': Subject.objects.all(),
            'selected_class_id': selected_class_id,
            'selected_subject_id': selected_subject_id,
            'students': students,
            'grades_matrix': grades_matrix,
            'grade_form': GradeForm(),
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Baho qo'yish ruxsati yo'q.")
        form = GradeForm(request.POST)
        if form.is_valid():
            grade = form.save()
            messages.success(request, f"{grade.student.first_name}ga {grade.score} baho qo'yildi!")
            if grade.student.user:
                send_system_notification(
                    grade.student.user, "Yangi Baho!",
                    f"{grade.subject.name} fanidan {grade.score} ball olindingiz.",
                    'EXAM', '/grades/'
                )
            return redirect(f'/grades/?class_id={grade.student.grade_class_id}&subject_id={grade.subject.id}')
        messages.error(request, "Baho kiritishda xatolik yuz berdi!")
        return redirect('gradebook')


# ── Attendance ────────────────────────────────────────────────

class AttendanceView(LoginRequiredMixin, View):
    def get(self, request):
        selected_class_id = request.GET.get('class_id')
        selected_subject_id = request.GET.get('subject_id')
        selected_date = request.GET.get('date', datetime.date.today().isoformat())
        students, existing_status = [], {}

        if selected_class_id and selected_subject_id:
            students = Student.objects.filter(grade_class_id=selected_class_id)
            attendances = Attendance.objects.filter(
                subject_id=selected_subject_id, date=selected_date, student__in=students
            )
            existing_status = {a.student_id: a.status for a in attendances}

        return render(request, 'attendance.html', {
            'classes': GradeClass.objects.all(),
            'subjects': Subject.objects.all(),
            'selected_class_id': selected_class_id,
            'selected_subject_id': selected_subject_id,
            'selected_date': selected_date,
            'students': students,
            'existing_status': existing_status,
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Yo'qlama qilish ruxsati yo'q.")
        class_id = request.POST.get('class_id')
        subject_id = request.POST.get('subject_id')
        date_str = request.POST.get('date')
        if class_id and subject_id and date_str:
            subject = get_object_or_404(Subject, pk=subject_id)
            for s in Student.objects.filter(grade_class_id=class_id):
                Attendance.objects.update_or_create(
                    student=s, subject=subject, date=date_str,
                    defaults={'status': request.POST.get(f'status_{s.id}', 'B')}
                )
            messages.success(request, "Davomat muvaffaqiyatli saqlandi!")
        return redirect(f'/attendance/?class_id={class_id}&subject_id={subject_id}&date={date_str}')


# ── Timetable ─────────────────────────────────────────────────

class TimetableView(LoginRequiredMixin, View):
    def get(self, request):
        classes = GradeClass.objects.all()
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
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN]:
            raise PermissionDenied("Dars jadvalini o'zgartirish ruxsati yo'q.")
        form = TimetableForm(request.POST)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.full_clean()
                obj.save()
                messages.success(request, "Dars jadvaliga dars qo'shildi!")
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else "Konflikt yuz berdi!")
        else:
            messages.error(request, "Formada xatoliklar mavjud!")
        return redirect('timetable')


# ── Fees & Payments ───────────────────────────────────────────

class FeeListView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT, Role.STUDENT, Role.PARENT]

    def get(self, request):
        role = get_user_role(request.user)
        if role == Role.STUDENT:
            fees = StudentFee.objects.filter(student=getattr(request.user, 'student_profile', None)).select_related('fee_type', 'student')
        elif role == Role.PARENT:
            parent = getattr(request.user, 'parent_profile', None)
            fees = StudentFee.objects.filter(student__in=parent.children.all() if parent else []).select_related('fee_type', 'student')
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
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT]

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
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT]

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


# ── Homework ──────────────────────────────────────────────────

class HomeworkListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        if role == Role.STUDENT:
            student = getattr(request.user, 'student_profile', None)
            homeworks = Homework.objects.filter(grade_class=student.grade_class).select_related('grade_class', 'subject') if student else Homework.objects.none()
        else:
            homeworks = Homework.objects.select_related('grade_class', 'subject', 'teacher').all()
        return render(request, 'homework.html', {'homeworks': homeworks, 'form': HomeworkForm()})

    def post(self, request):
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
            raise PermissionDenied("Vazifa yaratish ruxsati yo'q.")
        form = HomeworkForm(request.POST, request.FILES)
        if form.is_valid():
            hw = form.save()
            messages.success(request, "Yangi uyga vazifa e'lon qilindi!")
            for st in Student.objects.filter(grade_class=hw.grade_class):
                if st.user:
                    send_system_notification(
                        st.user, f"Yangi Uyga Vazifa: {hw.subject.name}",
                        f"{hw.title} (Muddat: {hw.due_date})", 'HOMEWORK', '/homework/'
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


# ── Exams ─────────────────────────────────────────────────────

class ExamListView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'exams.html', {
            'exams': Exam.objects.select_related('subject', 'grade_class').all(),
            'form': ExamForm(),
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
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
        return render(request, 'exam_results_entry.html', {
            'exam': exam,
            'students': Student.objects.filter(grade_class=exam.grade_class),
            'existing_results': {r.student_id: r for r in ExamResult.objects.filter(exam=exam)},
        })

    def post(self, request, exam_id):
        exam = get_object_or_404(Exam, pk=exam_id)
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
        # Recalculate ranks
        for rank, result in enumerate(ExamResult.objects.filter(exam=exam).order_by('-percentage'), 1):
            result.rank = rank
            result.save()
        messages.success(request, "Imtihon natijalari saqlandi va darajalar hisoblandi!")
        return redirect('exam_list')


# ── Announcements & Notifications ────────────────────────────

class AnnouncementListView(LoginRequiredMixin, View):
    def get(self, request):
        role = get_user_role(request.user)
        return render(request, 'announcements.html', {
            'announcements': Announcement.objects.select_related('created_by', 'grade_class').filter(
                Q(target_role='ALL') | Q(target_role=role)
            ),
            'form': AnnouncementForm(),
        })

    def post(self, request):
        if get_user_role(request.user) not in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
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
            student_id = request.POST.get('student_id')
            if student_id and get_user_role(request.user) in [Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER]:
                student = get_object_or_404(Student, pk=student_id)
            else:
                messages.error(request, "Test topshirish uchun O'quvchi profili biriktirilgan bo'lishi kerak!")
                return redirect('quiz_list')

        correct = sum(1 for q in questions if request.POST.get(f'q_{q.id}') == q.correct_option)
        total = questions.count()
        result = QuizResult.objects.create(
            student=student, quiz=quiz, score=correct, total_questions=total,
            percentage=round(correct / total * 100, 1) if total > 0 else 0
        )
        return render(request, 'quiz_result.html', {'result': result, 'quiz': quiz})


class LeaderboardView(LoginRequiredMixin, View):
    def get(self, request):
        results = QuizResult.objects.select_related('student__grade_class', 'quiz').order_by('-percentage', '-score')[:25]
        return render(request, 'leaderboard.html', {'results': results})


# ── Export (CSV) ──────────────────────────────────────────────

class ExportDataView(RoleRequiredMixin, View):
    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT, Role.TEACHER]

    def get(self, request, model_type):
        if model_type == 'students':
            return export_queryset_to_csv(
                Student.objects.select_related('grade_class').all(),
                ['student_id', 'first_name', 'last_name', 'grade_class__name', 'phone', 'parent_phone', 'status'],
                ['ID Kodi', 'Ismi', 'Familiyasi', 'Sinfi', 'Telefoni', 'Ota-ona Telefoni', 'Holati'],
                'oquvchilar_ruyxati.csv'
            )
        if model_type == 'fees':
            return export_queryset_to_csv(
                StudentFee.objects.select_related('student', 'fee_type').all(),
                ['student__student_id', 'student__first_name', 'student__last_name', 'fee_type__name', 'amount', 'status', 'due_date'],
                ["O'quvchi ID", 'Ismi', 'Familiyasi', "To'lov Turi", 'Summa', 'Holati', 'Muddati'],
                'tolovlar_ruyxati.csv'
            )
        if model_type == 'attendance':
            return export_queryset_to_csv(
                Attendance.objects.select_related('student', 'subject').all()[:500],
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