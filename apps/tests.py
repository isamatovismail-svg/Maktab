import datetime
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.models import Student, Grade, StudentFee, PaymentRecord, Exam, ExamResult, QuizResult
from apps.permissions import Role, get_user_role


# 1. MODEL TESTI (Baho chegara tekshiruvi)
@pytest.mark.django_db
def test_grade_rejects_out_of_range_score(school):
    grade = Grade(
        student=school.student_ali,
        teacher=school.teacher_a,
        subject=school.math,
        score=101,
        date=datetime.date.today(),
    )
    with pytest.raises(ValidationError):
        grade.save()


# 2. AUTH TESTI (Login)
@pytest.mark.django_db
def test_login_success(client, school):
    response = client.post(
        reverse("login"),
        {
            "username": "student_ali",
            "password": "password123",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("home")


# 3. VIEW TESTI (O'qituvchi baho qo'yishi)
@pytest.mark.django_db
def test_teacher_can_grade_own_student(client, school):
    client.login(username="teacher_a", password="password123")
    response = client.post(
        reverse("gradebook"),
        {
            "student": school.student_ali.pk,
            "subject": school.math.pk,
            "lesson": school.lesson_math.pk,
            "score": 5,
            "grade_type": "KUNDALIK",
            "date": datetime.date.today().isoformat(),
            "comment": "A'lo",
        },
    )
    assert response.status_code == 302
    assert Grade.objects.filter(
        student=school.student_ali,
        teacher=school.teacher_a,
        subject=school.math,
        score=5,
    ).exists()


# 4. PERMISSION TESTI (O'quvchi baho qo'ya olmasligi)
@pytest.mark.django_db
def test_student_cannot_submit_grades(client, school):
    client.login(username="student_ali", password="password123")
    response = client.post(
        reverse("gradebook"),
        {
            "student": school.student_ali.pk,
            "subject": school.math.pk,
            "score": 100,
            "grade_type": "KUNDALIK",
            "date": datetime.date.today().isoformat(),
        },
    )
    assert response.status_code == 403


# 5. SECURITY TESTI (Soxtalashtirilgan Request)
@pytest.mark.django_db
def test_tampered_teacher_id_is_rejected(client, school):
    client.login(username="teacher_a", password="password123")
    response = client.post(
        reverse("gradebook"),
        {
            "student": school.student_vali.pk,
            "subject": school.english.pk,
            "teacher": school.teacher_a.pk,
            "score": 5,
            "grade_type": "KUNDALIK",
            "date": datetime.date.today().isoformat(),
        },
    )
    assert response.status_code == 403