from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.models import UserProfile, Teacher, Student, GradeClass, Subject
from apps.permissions import Role
from django.utils import timezone


class Command(BaseCommand):
    help = "Demo o'quvchi va o'qituvchi foydalanuvchilarini yaratadi"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Demo foydalanuvchilar yaratilmoqda ===\n"))

        # --- O'QITUVCHI ---
        teacher_username = "demo_ustoz"
        teacher_password = "Ustoz@1234"

        if User.objects.filter(username=teacher_username).exists():
            self.stdout.write(self.style.WARNING(f"[!] '{teacher_username}' allaqachon mavjud — o'tkazib yuborildi."))
        else:
            teacher_user = User.objects.create_user(
                username=teacher_username,
                password=teacher_password,
                first_name="Ali",
                last_name="Karimov",
                email="ali.karimov@maktab.uz",
            )
            UserProfile.objects.create(user=teacher_user, role=Role.TEACHER)

            # Subject va GradeClass olish (yoki yaratish)
            subject, _ = Subject.objects.get_or_create(name="Matematika", defaults={"code": "MATH", "icon": "➕", "color": "#3B82F6"})
            grade_class, _ = GradeClass.objects.get_or_create(name="9-A")

            teacher_obj = Teacher.objects.create(
                user=teacher_user,
                first_name="Ali",
                last_name="Karimov",
                subject=subject,
                phone="+998901234567",
                qualification="Oliy toifali o'qituvchi",
                bio="Demo o'qituvchi foydalanuvchisi.",
            )
            teacher_obj.assigned_subjects.add(subject)
            teacher_obj.assigned_classes.add(grade_class)

            self.stdout.write(self.style.SUCCESS(f"[+] O'QITUVCHI yaratildi:"))
            self.stdout.write(f"     Login    : {teacher_username}")
            self.stdout.write(f"     Parol    : {teacher_password}")
            self.stdout.write(f"     Ism-Familiya: Ali Karimov")
            self.stdout.write(f"     Fan      : Matematika\n")

        # --- O'QUVCHI ---
        student_username = "demo_oquvchi"
        student_password = "Oquvchi@1234"

        if User.objects.filter(username=student_username).exists():
            self.stdout.write(self.style.WARNING(f"[!] '{student_username}' allaqachon mavjud — o'tkazib yuborildi."))
        else:
            student_user = User.objects.create_user(
                username=student_username,
                password=student_password,
                first_name="Zulfiya",
                last_name="Rahimova",
                email="zulfiya.rahimova@maktab.uz",
            )
            UserProfile.objects.create(user=student_user, role=Role.STUDENT)

            grade_class, _ = GradeClass.objects.get_or_create(name="9-A")

            Student.objects.create(
                user=student_user,
                first_name="Zulfiya",
                last_name="Rahimova",
                birth_date="2010-05-15",
                gender="F",
                grade_class=grade_class,
                phone="+998907654321",
                address="Toshkent sh., Yunusobod tumani",
                admission_date=timezone.now().date(),
                status="ACTIVE",
            )

            self.stdout.write(self.style.SUCCESS(f"[+] O'QUVCHI yaratildi:"))
            self.stdout.write(f"     Login    : {student_username}")
            self.stdout.write(f"     Parol    : {student_password}")
            self.stdout.write(f"     Ism-Familiya: Zulfiya Rahimova")
            self.stdout.write(f"     Sinf     : 9-A\n")

        self.stdout.write(self.style.SUCCESS("=== Tayyor! ==="))
