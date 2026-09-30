import datetime
import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.models import Student, Grade, PaymentRecord, Exam, ExamResult, QuizResult
from apps.permissions import Role, get_user_role


# ═══════════════════════════════════════════════════════════════
# 1. MODEL TESTLARI
# ═══════════════════════════════════════════════════════════════

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


@pytest.mark.django_db
def test_grade_rejects_cross_teacher_subject(school):
    grade = Grade(
        student=school.student_ali,
        teacher=school.teacher_a,
        subject=school.english,
        score=4,
        date=datetime.date.today(),
    )
    with pytest.raises(ValidationError):
        grade.save()


@pytest.mark.django_db
def test_student_fee_balance_due_uses_payments(student_fee):
    assert student_fee.net_amount == 900_000
    assert student_fee.balance_due == 900_000

    PaymentRecord.objects.create(
        student_fee=student_fee,
        paid_amount=400_000,
        payment_date=datetime.date.today(),
    )
    student_fee.refresh_from_db()
    assert student_fee.status == 'PARTIAL'
    assert student_fee.balance_due == 500_000


@pytest.mark.django_db
def test_exam_result_auto_percentage_and_grade(school):
    exam = Exam.objects.create(
        title='Chorak imtihoni',
        subject=school.math,
        grade_class=school.class_7a,
        exam_date=datetime.date.today(),
        total_marks=100,
    )
    result = ExamResult.objects.create(
        exam=exam,
        student=school.student_ali,
        marks_obtained=90,
        percentage=0,
        grade='',
    )
    result.refresh_from_db()
    assert result.percentage == 90.0
    assert result.grade == '5'


# ═══════════════════════════════════════════════════════════════
# 2. AUTH / VIEW'LAR
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_login_success(client, school):
    response = client.post(reverse('login'), {
        'username': 'student_ali',
        'password': 'password123',
    })
    assert response.status_code == 302
    assert response.url == reverse('home')


@pytest.mark.django_db
def test_login_failed(client):
    response = client.post(reverse('login'), {
        'username': 'yoq',
        'password': 'xato',
    })
    assert response.status_code == 200
    assert response.context['error']


@pytest.mark.django_db
def test_unauthenticated_redirects_to_login(client):
    response = client.get(reverse('gradebook'))
    assert response.status_code == 302
    assert reverse('login') in response.url


@pytest.mark.django_db
def test_admin_can_see_all_teachers(client, school):
    client.login(username='admin_user', password='password123')
    response = client.get(reverse('teacher_list'))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'Teacher A' in body
    assert 'Teacher B' in body


# 3. VIEW TESTI (O'qituvchi baho qo'yishi)
@pytest.mark.django_db
def test_teacher_can_grade_own_student(client, school):
    client.login(username='teacher_a', password='password123')
    response = client.post(reverse('gradebook'), {
        'student': school.student_ali.pk,
        'subject': school.math.pk,
        'lesson': school.lesson_math.pk,
        'score': 5,
        'grade_type': 'KUNDALIK',
        'date': datetime.date.today().isoformat(),
        'comment': "A'lo",
    })
    assert response.status_code == 302
    assert Grade.objects.filter(
        student=school.student_ali, teacher=school.teacher_a,
        subject=school.math, score=5,
    ).exists()


@pytest.mark.django_db
def test_cabinet_opens_for_student(client, school):
    client.login(username='student_ali', password='password123')
    response = client.get(reverse('cabinet'))
    assert response.status_code == 200
    assert 'Ali' in response.content.decode()


@pytest.mark.django_db
def test_quiz_take_saves_result(client, school, quiz):
    client.login(username='student_ali', password='password123')
    response = client.post(reverse('quiz_take', kwargs={'pk': quiz.pk}), {
        f'q_{quiz.questions.first().pk}': 'B',
    })
    assert response.status_code == 200
    result = QuizResult.objects.get(student=school.student_ali, quiz=quiz)
    assert result.score == 1
    assert result.percentage == 100.0


# ═══════════════════════════════════════════════════════════════
# 3. RUXSATLAR (permissions)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_teacher_cannot_grade_other_subject(client, school):
    client.login(username='teacher_a', password='password123')
    response = client.post(reverse('gradebook'), {
        'student': school.student_ali.pk,
        'subject': school.english.pk,
        'score': 5,
        'grade_type': 'KUNDALIK',
        'date': datetime.date.today().isoformat(),
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_cannot_edit_other_teacher_lesson(client, school):
    client.login(username='teacher_a', password='password123')
    response = client.get(
        reverse('lesson_update', kwargs={'pk': school.lesson_english.pk})
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_cannot_view_other_student_profile(client, school):
    client.login(username='student_ali', password='password123')
    response = client.get(
        reverse('student_profile', kwargs={'pk': school.student_vali.pk})
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_cannot_access_teacher_list(client, school):
    client.login(username='student_ali', password='password123')
    response = client.get(reverse('teacher_list'))
    assert response.status_code == 403


# 4. PERMISSION TESTI (O'quvchi baho qo'ya olmasligi)
@pytest.mark.django_db
def test_student_cannot_submit_grades(client, school):
    client.login(username='student_ali', password='password123')
    response = client.post(reverse('gradebook'), {
        'student': school.student_ali.pk,
        'subject': school.math.pk,
        'score': 100,
        'grade_type': 'KUNDALIK',
        'date': datetime.date.today().isoformat(),
    })
    assert response.status_code == 403


# 5. SECURITY TESTI (Soxtalashtirilgan Request)
@pytest.mark.django_db
def test_tampered_teacher_id_is_rejected(client, school):
    client.login(username='teacher_a', password='password123')
    response = client.post(reverse('gradebook'), {
        'student': school.student_vali.pk,
        'subject': school.english.pk,
        'teacher': school.teacher_a.pk,
        'score': 5,
        'grade_type': 'KUNDALIK',
        'date': datetime.date.today().isoformat(),
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_student_create_auto_generates_user(client, school):
    client.login(username='admin_user', password='password123')
    response = client.post(reverse('student_create'), {
        'first_name': 'Hasan',
        'last_name': 'Husanov',
        'gender': 'M',
        'status': 'ACTIVE',
        'phone': '+998901234567',
    })
    assert response.status_code == 302
    hasan = Student.objects.get(first_name='Hasan', last_name='Husanov')
    assert hasan.user is not None
    assert hasan.user.profile.role == Role.STUDENT


@pytest.mark.django_db
def test_get_user_role_for_each_account(school):
    assert get_user_role(school.admin_user) == Role.ADMIN
    assert get_user_role(school.teacher_a_user) == Role.TEACHER
    assert get_user_role(school.student_ali_user) == Role.STUDENT
    assert get_user_role(AnonymousUser()) is None


# ═══════════════════════════════════════════════════════════════
# 4. QO'SHIMCHA XAVFSIZLIK VA AUDIT TESTLARI
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_invoice_print_idor_blocked(client, school, student_fee):
    client.login(username='student_vali', password='password123')
    response = client.get(reverse('invoice_print', kwargs={'fee_id': student_fee.pk}))
    assert response.status_code == 403


@pytest.mark.django_db
def test_homework_cross_class_submission_blocked(client, school):
    from apps.models import Homework
    hw_7b = Homework.objects.create(
        grade_class=school.class_7b,
        subject=school.english,
        teacher=school.teacher_b,
        title="Unit 5 Essay",
        description="Write an essay",
        due_date=datetime.date.today(),
    )
    client.login(username='student_ali', password='password123')
    response = client.post(reverse('homework_submit', kwargs={'homework_id': hw_7b.pk}), {
        'submission_text': 'My unauthorized submission',
    })
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_deletion_cleans_up_user(client, school):
    client.login(username='admin_user', password='password123')
    user_to_delete = school.student_vali.user
    user_id = user_to_delete.id
    response = client.post(reverse('student_delete', kwargs={'pk': school.student_vali.pk}))
    assert response.status_code == 302
    from django.contrib.auth.models import User
    assert not User.objects.filter(id=user_id).exists()


@pytest.mark.django_db
def test_negative_financial_amount_rejected(student_fee):
    student_fee.amount = -500_000
    with pytest.raises(ValidationError):
        student_fee.full_clean()


@pytest.mark.django_db
def test_registration_always_creates_student(client):
    response = client.post(reverse('register'), {
        'username': 'new_user_1',
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'SecurePassword@123',
        'password2': 'SecurePassword@123',
        'role': 'TEACHER',
    })
    assert response.status_code == 302
    from django.contrib.auth.models import User
    new_user = User.objects.get(username='new_user_1')
    assert new_user.profile.role == Role.STUDENT


@pytest.mark.django_db
def test_telegram_bot_exact_verification(school):
    from asgiref.sync import async_to_sync
    from apps.bot import link_student_telegram

    st, err = async_to_sync(link_student_telegram)("Al", 999999)
    assert st is None
    assert err is not None

    st, err = async_to_sync(link_student_telegram)(school.student_ali.student_id, 999999)
    assert st is not None
    assert st.telegram_id == "999999"
    assert err is None
