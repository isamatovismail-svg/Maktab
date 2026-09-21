"""Umumiy pytest fixture'lar — testlarda qayta-qayta ma'lumot yaratmaslik uchun."""
import datetime
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User


@pytest.fixture(autouse=True)
def _test_http_settings(settings):
    """Prod SSL redirect test client'ni 301 ga urib yubormasligi uchun."""
    settings.DEBUG = True
    settings.SECURE_SSL_REDIRECT = False
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False

from apps.models import (
    UserProfile, Teacher, Student, GradeClass, Subject, Lesson,
    FeeType, StudentFee, Quiz, Question,
)
from apps.permissions import Role


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin_user',
        password='password123',
        email='admin@school.uz',
    )
    UserProfile.objects.create(user=user, role=Role.ADMIN)
    return user


@pytest.fixture
def school(db, admin_user):
    """Maktabning asosiy test ma'lumotlari: 2 fan, 2 sinf, 2 o'qituvchi, 2 o'quvchi."""
    math = Subject.objects.create(name='Matematika', code='MATH101', icon='📐')
    english = Subject.objects.create(name='Ingliz tili', code='ENG101', icon='🇬🇧')

    class_7a = GradeClass.objects.create(name='7-A')
    class_7b = GradeClass.objects.create(name='7-B')

    teacher_a_user = User.objects.create_user(
        username='teacher_a', password='password123',
        first_name='Teacher', last_name='A',
    )
    UserProfile.objects.create(user=teacher_a_user, role=Role.TEACHER)
    teacher_a = Teacher.objects.create(
        user=teacher_a_user, first_name='Teacher', last_name='A',
        subject=math, phone='+998901',
    )
    teacher_a.assigned_subjects.add(math)
    teacher_a.assigned_classes.add(class_7a)

    teacher_b_user = User.objects.create_user(
        username='teacher_b', password='password123',
        first_name='Teacher', last_name='B',
    )
    UserProfile.objects.create(user=teacher_b_user, role=Role.TEACHER)
    teacher_b = Teacher.objects.create(
        user=teacher_b_user, first_name='Teacher', last_name='B',
        subject=english, phone='+998902',
    )
    teacher_b.assigned_subjects.add(english)
    teacher_b.assigned_classes.add(class_7b)

    student_ali_user = User.objects.create_user(
        username='student_ali', password='password123',
        first_name='Ali', last_name='Karimov',
    )
    UserProfile.objects.create(user=student_ali_user, role=Role.STUDENT)
    student_ali = Student.objects.create(
        user=student_ali_user, first_name='Ali', last_name='Karimov',
        grade_class=class_7a,
    )

    student_vali_user = User.objects.create_user(
        username='student_vali', password='password123',
        first_name='Vali', last_name='Toshev',
    )
    UserProfile.objects.create(user=student_vali_user, role=Role.STUDENT)
    student_vali = Student.objects.create(
        user=student_vali_user, first_name='Vali', last_name='Toshev',
        grade_class=class_7b,
    )

    lesson_math = Lesson.objects.create(
        title='Algebra Asoslari', subject=math, teacher=teacher_a,
        grade_class=class_7a, date=datetime.date.today(),
    )
    lesson_english = Lesson.objects.create(
        title='Grammar Basics', subject=english, teacher=teacher_b,
        grade_class=class_7b, date=datetime.date.today(),
    )

    return SimpleNamespace(
        admin_user=admin_user,
        math=math,
        english=english,
        class_7a=class_7a,
        class_7b=class_7b,
        teacher_a_user=teacher_a_user,
        teacher_a=teacher_a,
        teacher_b_user=teacher_b_user,
        teacher_b=teacher_b,
        student_ali_user=student_ali_user,
        student_ali=student_ali,
        student_vali_user=student_vali_user,
        student_vali=student_vali,
        lesson_math=lesson_math,
        lesson_english=lesson_english,
    )


@pytest.fixture
def fee_type(db):
    return FeeType.objects.create(name='Kontrakt', amount=1_000_000)


@pytest.fixture
def student_fee(school, fee_type):
    return StudentFee.objects.create(
        student=school.student_ali,
        fee_type=fee_type,
        amount=1_000_000,
        discount_amount=100_000,
        due_date=datetime.date.today(),
        status='PENDING',
    )


@pytest.fixture
def quiz(school):
    q = Quiz.objects.create(
        title='Algebra testi',
        subject=school.math,
        grade_level=7,
        time_limit_minutes=15,
    )
    Question.objects.create(
        quiz=q,
        text='2 + 2 = ?',
        option_a='3',
        option_b='4',
        option_c='5',
        option_d='6',
        correct_option='B',
    )
    return q
