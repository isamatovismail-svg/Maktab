from django.contrib import admin
from .models import GradeClass, Subject, Teacher, Student, Timetable, Grade, Attendance, Homework, Quiz, Question, QuizResult

@admin.register(GradeClass)
class GradeClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_teacher')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'color')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'subject', 'phone')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'grade_class', 'phone', 'parent_phone', 'telegram_id')
    list_filter = ('grade_class',)
    search_fields = ('first_name', 'last_name', 'phone', 'parent_phone')

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('grade_class', 'day_of_week', 'time_slot', 'subject', 'teacher', 'room')
    list_filter = ('grade_class', 'day_of_week', 'subject')

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'score', 'grade_type', 'date')
    list_filter = ('grade_type', 'subject', 'date')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status', 'notified_telegram')
    list_filter = ('status', 'date', 'subject')

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ('grade_class', 'subject', 'title', 'due_date')
    list_filter = ('grade_class', 'subject')

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
