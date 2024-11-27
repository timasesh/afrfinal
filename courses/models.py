from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.exceptions import ValidationError


class User(AbstractUser):
    is_student = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    video = models.FileField(upload_to='videos/', null=True, blank=True)  # Позволить NULL и пустое значение
    pdf = models.FileField(upload_to='pdfs/', null=True, blank=True)

    def __str__(self):
        return self.title


class Quiz(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    def questions(self):
        return self.question_set.all()


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


class Answer(models.Model):
    text = models.CharField(max_length=255)  # Текст ответа
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)  # Правильный ли ответ

    def __str__(self):
        return f'{self.text} ({"Правильный" if self.is_correct else "Неправильный"})'


class Module(models.Model):
    title = models.CharField(max_length=100)
    lessons = models.ManyToManyField(Lesson)
    description = models.TextField(null=True, blank=True, default="")
    quizzes = models.ManyToManyField(Quiz, blank=True)  # Связь с квизами

    def __str__(self):
        return self.title
import random
import string
class Course(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    modules = models.ManyToManyField('Module', blank=True)
    course_code = models.CharField(max_length=5, blank=True, unique=True)
    students = models.ManyToManyField('Student', related_name='enrolled_courses', blank=True)
    image = models.ImageField(upload_to='image/', null=True, blank=True)  # Новое поле для изображения

    def save(self, *args, **kwargs):
        if not self.course_code:
            self.course_code = self.generate_course_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def generate_course_code(self, length=5):
        """Генерация случайного кода для курса."""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if not Course.objects.filter(course_code=code).exists():
                return code

from django.core.validators import MinValueValidator, MaxValueValidator


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    courses = models.ManyToManyField('Course', related_name='students_set')
    department = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],  # Ограничение диапазона от 1 до 12
        null=True,
        blank=True,
        verbose_name="Департамент"
    )

    def __str__(self):
        return self.user.username

# class Student(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     courses = models.ManyToManyField('Course', related_name='students_list', blank=True)  # Измените имя на 'students_list'
#
#     def __str__(self):
#         return self.user.username

class CourseProgress(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    progress = models.FloatField(default=0.0)  # Прогресс в процентах

    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.module.title} - {self.lesson.title}"


from django.conf import settings
class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    date_taken = models.DateTimeField()  # Поле для даты и времени прохождения квиза

    def __str__(self):
        return f'{self.user} - {self.quiz} - {self.score} - {self.date_taken}'

class UploadedFile(models.Model):
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

