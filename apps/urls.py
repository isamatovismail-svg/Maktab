from django.urls import path
from .views import (
    UserLoginView, UserRegisterView, UserLogoutView,
    HomeView, StudentListView, StudentCreateView, StudentUpdateView, StudentDeleteView,
    GradeBookView, AttendanceView, TimetableView, HomeworkListView,
    QuizListView, QuizTakeView, LeaderboardView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('logout/', UserLogoutView.as_view(), name='logout'),

    # O'quvchilar
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/add/', StudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/edit/', StudentUpdateView.as_view(), name='student_update'),
    path('students/<int:pk>/delete/', StudentDeleteView.as_view(), name='student_delete'),

    # Elektron Kundalik (Baholar & Davomat & Jadval & Vazifalar)
    path('grades/', GradeBookView.as_view(), name='gradebook'),
    path('attendance/', AttendanceView.as_view(), name='attendance'),
    path('timetable/', TimetableView.as_view(), name='timetable'),
    path('homework/', HomeworkListView.as_view(), name='homework_list'),

    # Bilim.uz Test Platformasi
    path('quizzes/', QuizListView.as_view(), name='quiz_list'),
    path('quizzes/<int:pk>/take/', QuizTakeView.as_view(), name='quiz_take'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]
