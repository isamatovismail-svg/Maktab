from django.urls import path
from .views import *

urlpatterns = [
    path('', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/add/',StudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/edit/',StudentUpdateView.as_view(), name='student_update'),
    path('students/<int:pk>/delete/',StudentDeleteView.as_view(), name='student_delete'),
    path('lessons/',LessonListView.as_view(), name='lesson_list'),
    path('lessons/add/',LessonCreateView.as_view(), name='lesson_create'),
    path('lessons/<int:pk>/edit/',LessonUpdateView.as_view(), name='lesson_update'),
    path('lessons/<int:pk>/delete/',LessonDeleteView.as_view(), name='lesson_delete'),
]
