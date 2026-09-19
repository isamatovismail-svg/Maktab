from django.urls import path
from .views import (
    # Auth
    UserLoginView, UserRegisterView, UserLogoutView,
    # Dashboard
    HomeView,
    # Teachers
    TeacherListView, TeacherCreateView, TeacherUpdateView, TeacherDeleteView,
    # Students
    StudentListView, StudentProfileView, StudentCreateView, StudentUpdateView, StudentDeleteView,
    # Subjects
    SubjectListView,
    # Lessons
    LessonListView, LessonCreateView, LessonUpdateView, LessonDeleteView,
    # Grades
    GradeBookView,
    # Attendance
    AttendanceView,
    # Timetable
    TimetableView,
    # Fees
    FeeListView, StudentFeeCreateView, PaymentRecordCreateView, InvoicePrintView,
    # Homework
    HomeworkListView, HomeworkSubmitView,
    # Exams
    ExamListView, ExamResultEntryView,
    # Announcements & Notifications
    AnnouncementListView, NotificationListView, MarkNotificationReadView,
    # Quizzes
    QuizListView, QuizTakeView,
    # Export
    ExportDataView,
)

urlpatterns = [
    # ── Autentifikatsiya ──────────────────────────────────────
    path('', HomeView.as_view(), name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(), name='logout'),

    # ── O'qituvchilar ─────────────────────────────────────────
    path('teachers/', TeacherListView.as_view(), name='teacher_list'),
    path('teachers/add/', TeacherCreateView.as_view(), name='teacher_create'),
    path('teachers/<int:pk>/edit/', TeacherUpdateView.as_view(), name='teacher_update'),
    path('teachers/<int:pk>/delete/', TeacherDeleteView.as_view(), name='teacher_delete'),

    # ── O'quvchilar ───────────────────────────────────────────
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/add/', StudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/', StudentProfileView.as_view(), name='student_profile'),
    path('students/<int:pk>/edit/', StudentUpdateView.as_view(), name='student_update'),
    path('students/<int:pk>/delete/', StudentDeleteView.as_view(), name='student_delete'),

    # ── Fanlar ────────────────────────────────────────────────
    path('subjects/', SubjectListView.as_view(), name='subject_list'),

    # ── Darslar ───────────────────────────────────────────────
    path('lessons/', LessonListView.as_view(), name='lesson_list'),
    path('lessons/add/', LessonCreateView.as_view(), name='lesson_create'),
    path('lessons/<int:pk>/edit/', LessonUpdateView.as_view(), name='lesson_update'),
    path('lessons/<int:pk>/delete/', LessonDeleteView.as_view(), name='lesson_delete'),

    # ── Baholar Jurnali ───────────────────────────────────────
    path('grades/', GradeBookView.as_view(), name='gradebook'),

    # ── Yo'qlama / Davomat ────────────────────────────────────
    path('attendance/', AttendanceView.as_view(), name='attendance'),

    # ── Dars Jadvali ──────────────────────────────────────────
    path('timetable/', TimetableView.as_view(), name='timetable'),

    # ── Uyga Vazifalar ────────────────────────────────────────
    path('homework/', HomeworkListView.as_view(), name='homework_list'),
    path('homework/<int:homework_id>/submit/', HomeworkSubmitView.as_view(), name='homework_submit'),

    # ── To'lovlar ─────────────────────────────────────────────
    path('fees/', FeeListView.as_view(), name='fee_list'),
    path('fees/add/', StudentFeeCreateView.as_view(), name='fee_create'),
    path('fees/<int:fee_id>/pay/', PaymentRecordCreateView.as_view(), name='payment_create'),
    path('fees/<int:fee_id>/invoice/', InvoicePrintView.as_view(), name='invoice_print'),

    # ── Imtihonlar ────────────────────────────────────────────
    path('exams/', ExamListView.as_view(), name='exam_list'),
    path('exams/<int:exam_id>/results/', ExamResultEntryView.as_view(), name='exam_results'),

    # ── E'lonlar va Xabarnomalar ──────────────────────────────
    path('announcements/', AnnouncementListView.as_view(), name='announcement_list'),
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification_read'),

    # ── Bilim.uz Test Platformasi ─────────────────────────────
    path('quizzes/', QuizListView.as_view(), name='quiz_list'),
    path('quizzes/<int:pk>/take/', QuizTakeView.as_view(), name='quiz_take'),

    # ── Export ────────────────────────────────────────────────
    path('export/<str:model_type>/', ExportDataView.as_view(), name='export_data'),
]
