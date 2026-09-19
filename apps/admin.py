from django.contrib import admin
from .models import (
    UserProfile, GradeClass, Subject, ParentProfile, Teacher, Student,
    Timetable, Lesson, Grade, Attendance, FeeType, StudentFee, PaymentRecord,
    Homework, HomeworkSubmission, Exam, ExamResult, Announcement,
    Notification, Quiz, Question, QuizResult
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')


@admin.register(GradeClass)
class GradeClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_teacher')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'color')


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'email')
    search_fields = ('first_name', 'last_name', 'phone')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'subject', 'phone', 'qualification')
    search_fields = ('first_name', 'last_name', 'phone')
    filter_horizontal = ('assigned_subjects', 'assigned_classes')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'grade_class', 'status', 'phone', 'parent_phone', 'telegram_id')
    list_filter = ('grade_class', 'status', 'gender')
    search_fields = ('student_id', 'first_name', 'last_name', 'phone', 'parent_phone')


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('grade_class', 'day_of_week', 'time_slot', 'subject', 'teacher', 'room')
    list_filter = ('grade_class', 'day_of_week', 'subject')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'teacher', 'grade_class', 'date')
    list_filter = ('subject', 'grade_class', 'date')
    search_fields = ('title', 'teacher__first_name', 'teacher__last_name', 'description')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'subject', 'lesson', 'score', 'grade_type', 'date')
    list_filter = ('grade_type', 'subject', 'teacher', 'date')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status', 'notified_telegram')
    list_filter = ('status', 'date', 'subject')


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount')


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_type', 'amount', 'discount_amount', 'status', 'due_date')
    list_filter = ('status', 'fee_type', 'academic_year')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_id')


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'student_fee', 'paid_amount', 'payment_method', 'payment_date')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('receipt_number', 'transaction_id')


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ('grade_class', 'subject', 'teacher', 'title', 'due_date')
    list_filter = ('grade_class', 'subject')


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = ('homework', 'student', 'submitted_at', 'status', 'score')
    list_filter = ('status', 'submitted_at')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'grade_class', 'exam_date', 'total_marks')
    list_filter = ('grade_class', 'subject', 'exam_date')


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'marks_obtained', 'percentage', 'grade', 'rank')
    list_filter = ('grade', 'exam')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_role', 'grade_class', 'created_by', 'created_at')
    list_filter = ('target_role', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 4


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'grade_level', 'time_limit_minutes')
    inlines = [QuestionInline]


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'total_questions', 'percentage', 'completed_at')
    list_filter = ('quiz', 'completed_at')
