from django.db import models

class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Ismi")
    last_name = models.CharField(max_length=100, verbose_name="Familiyasi")
    phone = models.CharField(max_length=20, verbose_name="Telefon raqami")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Lesson(models.Model):
    title = models.CharField(max_length=150, verbose_name="Fan nomi")
    teacher_name = models.CharField(max_length=100, verbose_name="O'qituvchi nomi")
    
    def __str__(self):
        return self.title
