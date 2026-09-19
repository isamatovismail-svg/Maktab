import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.models import UserProfile, Teacher, Student, GradeClass, Subject, Lesson, Grade
from apps.permissions import Role


class RoleAuthorizationSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin User
        self.admin_user = User.objects.create_superuser(
            username='admin_user', password='password123', email='admin@school.uz'
        )
        UserProfile.objects.create(user=self.admin_user, role=Role.ADMIN)

        # 2. Create Subjects
        self.math = Subject.objects.create(name='Matematika', code='MATH101')
        self.english = Subject.objects.create(name='Ingliz tili', code='ENG101')

        # 3. Create Classes
        self.class_7a = GradeClass.objects.create(name='7-A')
        self.class_7b = GradeClass.objects.create(name='7-B')

        # 4. Create Teacher A (Math -> 7-A)
        self.teacher_a_user = User.objects.create_user(
            username='teacher_a', password='password123', first_name='Teacher', last_name='A'
        )
        UserProfile.objects.create(user=self.teacher_a_user, role=Role.TEACHER)
        self.teacher_a = Teacher.objects.create(
            user=self.teacher_a_user, first_name='Teacher', last_name='A', subject=self.math, phone='+998901'
        )
        self.teacher_a.assigned_subjects.add(self.math)
        self.teacher_a.assigned_classes.add(self.class_7a)

        # 5. Create Teacher B (English -> 7-B)
        self.teacher_b_user = User.objects.create_user(
            username='teacher_b', password='password123', first_name='Teacher', last_name='B'
        )
        UserProfile.objects.create(user=self.teacher_b_user, role=Role.TEACHER)
        self.teacher_b = Teacher.objects.create(
            user=self.teacher_b_user, first_name='Teacher', last_name='B', subject=self.english, phone='+998902'
        )
        self.teacher_b.assigned_subjects.add(self.english)
        self.teacher_b.assigned_classes.add(self.class_7b)

        # 6. Create Student Ali (7-A) and Student Vali (7-B)
        self.student_ali_user = User.objects.create_user(
            username='student_ali', password='password123', first_name='Ali', last_name='Karimov'
        )
        UserProfile.objects.create(user=self.student_ali_user, role=Role.STUDENT)
        self.student_ali = Student.objects.create(
            user=self.student_ali_user, first_name='Ali', last_name='Karimov', grade_class=self.class_7a
        )

        self.student_vali_user = User.objects.create_user(
            username='student_vali', password='password123', first_name='Vali', last_name='Toshev'
        )
        UserProfile.objects.create(user=self.student_vali_user, role=Role.STUDENT)
        self.student_vali = Student.objects.create(
            user=self.student_vali_user, first_name='Vali', last_name='Toshev', grade_class=self.class_7b
        )

        # 7. Create Lesson for Teacher A and Lesson for Teacher B
        self.lesson_math = Lesson.objects.create(
            title='Algebra Asoslari', subject=self.math, teacher=self.teacher_a,
            grade_class=self.class_7a, date=datetime.date.today()
        )

        self.lesson_english = Lesson.objects.create(
            title='Grammar Basics', subject=self.english, teacher=self.teacher_b,
            grade_class=self.class_7b, date=datetime.date.today()
        )

    # Test 1: Admin can access all teachers
    def test_01_admin_can_access_all_teachers(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('teacher_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher A')
        self.assertContains(response, 'Teacher B')

    # Test 2: Admin can access all students
    def test_02_admin_can_access_all_students(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ali')
        self.assertContains(response, 'Vali')

    # Test 3: Teacher A can access their own subject/lessons
    def test_03_teacher_a_can_access_own_subject(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.get(reverse('lesson_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Algebra Asoslari')
        self.assertNotContains(response, 'Grammar Basics')

    # Test 4: Teacher A cannot access/edit Teacher B's lesson
    def test_04_teacher_a_cannot_edit_teacher_b_lesson(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.get(reverse('lesson_update', kwargs={'pk': self.lesson_english.pk}))
        self.assertEqual(response.status_code, 403)

    # Test 5: Teacher A can grade their assigned student for Math
    def test_05_teacher_a_can_grade_assigned_student(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_ali.pk,
            'subject': self.math.pk,
            'lesson': self.lesson_math.pk,
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
            'comment': 'A\'lo'
        })
        self.assertEqual(response.status_code, 302)
        grade_exists = Grade.objects.filter(
            student=self.student_ali, teacher=self.teacher_a, subject=self.math, score=5
        ).exists()
        self.assertTrue(grade_exists)

    # Test 6: Teacher A cannot grade a student for Teacher B's subject
    def test_06_teacher_a_cannot_grade_for_teacher_b_subject(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_ali.pk,
            'subject': self.english.pk, # English belongs to Teacher B!
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403) # Forbidden!

    # Test 7: Teacher A cannot edit Teacher B's grade at model/DB level
    def test_07_model_level_validation_rejects_cross_teacher_grading(self):
        grade = Grade(
            student=self.student_ali,
            teacher=self.teacher_a, # Teacher A
            subject=self.english,  # English (Teacher A is NOT assigned)
            score=4,
            date=datetime.date.today()
        )
        with self.assertRaises(ValidationError):
            grade.save()

    # Test 8: Student A can see their own grades
    def test_08_student_can_see_own_grades(self):
        Grade.objects.create(
            student=self.student_ali, teacher=self.teacher_a, subject=self.math,
            score=5, date=datetime.date.today(), grade_type='KUNDALIK'
        )
        self.client.login(username='student_ali', password='password123')
        response = self.client.get(reverse('gradebook'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Matematika')

    # Test 9: Student A cannot see Student B's profile
    def test_09_student_a_cannot_see_student_b_profile(self):
        self.client.login(username='student_ali', password='password123')
        response = self.client.get(reverse('student_profile', kwargs={'pk': self.student_vali.pk}))
        self.assertEqual(response.status_code, 403)

    # Test 10: Student cannot access admin routes
    def test_10_student_cannot_access_admin_routes(self):
        self.client.login(username='student_ali', password='password123')
        response = self.client.get(reverse('teacher_list'))
        self.assertEqual(response.status_code, 403)

    # Test 11: Teacher cannot access admin routes
    def test_11_teacher_cannot_access_admin_teacher_create(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.get(reverse('teacher_create'))
        self.assertEqual(response.status_code, 403)

    # Test 12: Changing IDs manually in API requests cannot bypass permissions
    def test_12_changing_ids_manually_cannot_bypass_permissions(self):
        self.client.login(username='teacher_a', password='password123')
        # Teacher A attempts to assign self as teacher to Teacher B's English lesson
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_vali.pk, # 7-B student
            'subject': self.english.pk,      # Teacher B subject
            'teacher': self.teacher_a.pk,    # Tampered Teacher ID
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403)
