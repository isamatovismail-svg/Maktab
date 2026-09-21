import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.models import UserProfile, Teacher, Student, GradeClass, Subject, Lesson, Grade
from apps.permissions import Role


class MaktabSystemTests(TestCase):
    """
    Tizimning eng muhim 10 ta testi.
    Xavfsizlik, ruxsatlar va asosiy funksiyalar tekshiriladi.
    """

    def setUp(self):
        """Har bir test uchun umumiy test ma'lumotlari yaratiladi."""
        self.client = Client()

        # Admin
        self.admin_user = User.objects.create_superuser(
            username='admin_user', password='password123', email='admin@school.uz'
        )
        UserProfile.objects.create(user=self.admin_user, role=Role.ADMIN)

        # Fanlar
        self.math = Subject.objects.create(name='Matematika', code='MATH101')
        self.english = Subject.objects.create(name='Ingliz tili', code='ENG101')

        # Sinflar
        self.class_7a = GradeClass.objects.create(name='7-A')
        self.class_7b = GradeClass.objects.create(name='7-B')

        # O'qituvchi A — Matematika, 7-A sinfi
        self.teacher_a_user = User.objects.create_user(
            username='teacher_a', password='password123', first_name='Teacher', last_name='A'
        )
        UserProfile.objects.create(user=self.teacher_a_user, role=Role.TEACHER)
        self.teacher_a = Teacher.objects.create(
            user=self.teacher_a_user, first_name='Teacher', last_name='A',
            subject=self.math, phone='+998901'
        )
        self.teacher_a.assigned_subjects.add(self.math)
        self.teacher_a.assigned_classes.add(self.class_7a)

        # O'qituvchi B — Ingliz tili, 7-B sinfi
        self.teacher_b_user = User.objects.create_user(
            username='teacher_b', password='password123', first_name='Teacher', last_name='B'
        )
        UserProfile.objects.create(user=self.teacher_b_user, role=Role.TEACHER)
        self.teacher_b = Teacher.objects.create(
            user=self.teacher_b_user, first_name='Teacher', last_name='B',
            subject=self.english, phone='+998902'
        )
        self.teacher_b.assigned_subjects.add(self.english)
        self.teacher_b.assigned_classes.add(self.class_7b)

        # O'quvchi Ali — 7-A sinfi
        self.student_ali_user = User.objects.create_user(
            username='student_ali', password='password123', first_name='Ali', last_name='Karimov'
        )
        UserProfile.objects.create(user=self.student_ali_user, role=Role.STUDENT)
        self.student_ali = Student.objects.create(
            user=self.student_ali_user, first_name='Ali', last_name='Karimov',
            grade_class=self.class_7a
        )

        # O'quvchi Vali — 7-B sinfi
        self.student_vali_user = User.objects.create_user(
            username='student_vali', password='password123', first_name='Vali', last_name='Toshev'
        )
        UserProfile.objects.create(user=self.student_vali_user, role=Role.STUDENT)
        self.student_vali = Student.objects.create(
            user=self.student_vali_user, first_name='Vali', last_name='Toshev',
            grade_class=self.class_7b
        )

        # Darslar
        self.lesson_math = Lesson.objects.create(
            title='Algebra Asoslari', subject=self.math, teacher=self.teacher_a,
            grade_class=self.class_7a, date=datetime.date.today()
        )
        self.lesson_english = Lesson.objects.create(
            title='Grammar Basics', subject=self.english, teacher=self.teacher_b,
            grade_class=self.class_7b, date=datetime.date.today()
        )

    # ─────────────────────────────────────────────────────────
    # TEST 1: Admin barcha o'qituvchilarni ko'ra oladi
    # Sabab: Admin tizimning to'liq nazoratchi — barcha ma'lumotlarga
    # kirishi shart. Agar bu ishlamasa, admin paneli umuman foydasiz.
    # ─────────────────────────────────────────────────────────
    def test_01_admin_can_see_all_teachers(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('teacher_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher A')
        self.assertContains(response, 'Teacher B')

    # ─────────────────────────────────────────────────────────
    # TEST 2: O'qituvchi o'z o'quvchisiga baho qo'ya oladi
    # Sabab: Tizimning asosiy vazifasi — baholash. Agar o'qituvchi
    # o'z sinfidagi o'quvchiga baho qo'ya olmasa, butun tizim ishlamaydi.
    # ─────────────────────────────────────────────────────────
    def test_02_teacher_can_grade_own_student(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_ali.pk,
            'subject': self.math.pk,
            'lesson': self.lesson_math.pk,
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
            'comment': "A'lo"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Grade.objects.filter(
                student=self.student_ali, teacher=self.teacher_a,
                subject=self.math, score=5
            ).exists()
        )

    # ─────────────────────────────────────────────────────────
    # TEST 3: O'qituvchi boshqa o'qituvchi faniga baho qo'ya olmaydi
    # Sabab: Xavfsizlik. O'qituvchi A Ingliz tili faniga baho qo'ysa —
    # bu Teacher B ning vakolatiga tajovuz. 403 qaytishi shart.
    # ─────────────────────────────────────────────────────────
    def test_03_teacher_cannot_grade_other_teacher_subject(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_ali.pk,
            'subject': self.english.pk,  # Ingliz tili — Teacher B ning fani!
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 4: Model darajasida noto'g'ri baho saqlanmaydi (DB himoyasi)
    # Sabab: View darajasidagi tekshiruv chetlab o'tilsa ham, model
    # o'zining ValidationError'i bilan ikkinchi qatlamda himoya qiladi.
    # Bu ikki qatlamli xavfsizlikni ta'minlaydi.
    # ─────────────────────────────────────────────────────────
    def test_04_model_rejects_cross_teacher_grade_at_db_level(self):
        grade = Grade(
            student=self.student_ali,
            teacher=self.teacher_a,   # Teacher A
            subject=self.english,     # Lekin Ingliz tili — Teacher A biriktirilmagan!
            score=4,
            date=datetime.date.today()
        )
        with self.assertRaises(ValidationError):
            grade.save()

    # ─────────────────────────────────────────────────────────
    # TEST 5: O'qituvchi boshqa o'qituvchi darsini tahrirlay olmaydi
    # Sabab: IDOR (Insecure Direct Object Reference) himoyasi.
    # URL dagi ID ni o'zgartirib boshqa darsga kirish mumkin bo'lmasligi kerak.
    # ─────────────────────────────────────────────────────────
    def test_05_teacher_cannot_edit_other_teacher_lesson(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.get(
            reverse('lesson_update', kwargs={'pk': self.lesson_english.pk})
        )
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 6: O'quvchi boshqa o'quvchi profilini ko'ra olmaydi
    # Sabab: Maxfiylik. Har bir o'quvchi faqat o'z ma'lumotlarini
    # ko'rishi kerak. Boshqa o'quvchi ID sini URL ga yozib kirish — 403.
    # ─────────────────────────────────────────────────────────
    def test_06_student_cannot_view_other_student_profile(self):
        self.client.login(username='student_ali', password='password123')
        response = self.client.get(
            reverse('student_profile', kwargs={'pk': self.student_vali.pk})
        )
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 7: O'quvchi admin sahifalariga kira olmaydi
    # Sabab: Rolga asoslangan ruxsat tizimi to'g'ri ishlashini tekshiradi.
    # O'quvchi teacher_list sahifasiga kirsa — 403 olishi shart.
    # ─────────────────────────────────────────────────────────
    def test_07_student_cannot_access_admin_pages(self):
        self.client.login(username='student_ali', password='password123')
        response = self.client.get(reverse('teacher_list'))
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 8: O'quvchi baho kirita olmaydi
    # Sabab: Faqat Admin va O'qituvchi baho qo'yishi mumkin.
    # O'quvchi o'z bahosini o'zi kiritib yubormasligi — kritik xavfsizlik.
    # ─────────────────────────────────────────────────────────
    def test_08_student_cannot_submit_grades(self):
        self.client.login(username='student_ali', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_ali.pk,
            'subject': self.math.pk,
            'score': 100,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 9: ID ni qo'lda o'zgartirib ruxsatdan o'tib bo'lmaydi
    # Sabab: Eng xavfli hujum turi — POST so'rovda teacher ID ni
    # qo'lda o'zgartirib, boshqa o'qituvchi sifatida baho kiritish.
    # Bu tamper attack — 403 qaytishi shart.
    # ─────────────────────────────────────────────────────────
    def test_09_tampered_teacher_id_in_request_is_rejected(self):
        self.client.login(username='teacher_a', password='password123')
        response = self.client.post(reverse('gradebook'), {
            'student': self.student_vali.pk,  # 7-B o'quvchisi
            'subject': self.english.pk,       # Teacher B ning fani
            'teacher': self.teacher_a.pk,     # O'zini Teacher sifatida ko'rsatishga urinish!
            'score': 5,
            'grade_type': 'KUNDALIK',
            'date': datetime.date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 403)

    # ─────────────────────────────────────────────────────────
    # TEST 10: Admin o'quvchi qo'shganda avtomatik User yaratiladi
    # Sabab: Admin qo'lda User yaratishi shart emas — tizim avtomatik
    # yaratishi kerak. Student.user null bo'lmasligi va role='STUDENT'
    # bo'lishi — tizim integratsiyasining to'g'ri ishlashini isbotlaydi.
    # ─────────────────────────────────────────────────────────
    def test_10_admin_student_create_auto_generates_user(self):
        self.client.login(username='admin_user', password='password123')
        response = self.client.post(reverse('student_create'), {
            'first_name': 'Hasan',
            'last_name': 'Husanov',
            'gender': 'M',
            'status': 'ACTIVE',
            'phone': '+998901234567',
        })
        self.assertEqual(response.status_code, 302)
        hasan = Student.objects.get(first_name='Hasan', last_name='Husanov')
        self.assertIsNotNone(hasan.user)                          # User yaratilganmi?
        self.assertEqual(hasan.user.profile.role, Role.STUDENT)  # Roli to'g'rimi?
