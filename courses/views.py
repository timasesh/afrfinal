from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import StudentRegistrationForm, LessonCreationForm, ModuleCreationForm, CourseCreationForm
from .models import User, Lesson, Module, Course, CourseProgress, Student

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Проверяем тип пользователя и перенаправляем на соответствующую страницу
            if user.is_admin:
                return redirect('admin_page')  # Перенаправление для админа
            elif user.is_student:
                return redirect('student_page')  # Перенаправление для студента
        else:
            # Обработка ошибки аутентификации
            error_message = "Неверные учетные данные."
            return render(request, 'courses/login.html', {'error': error_message})

    return render(request, 'courses/login.html')

def student_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and hasattr(user, 'student'):  # Проверка роли студента
            login(request, user)
            return redirect('student_page')  # Перенаправление на страницу студента
        else:
            return HttpResponse('Invalid login or not a student.')
    return render(request, 'courses/student_login.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:  # Проверка роли администратора
            login(request, user)
            return redirect('admin_page')
        else:
            return HttpResponse('Invalid login or not an admin.')
    return render(request, 'courses/admin_login.html')
@login_required
def admin_page(request):
    student_form = StudentRegistrationForm()
    lesson_form = LessonCreationForm()
    module_form = ModuleCreationForm()
    course_form = CourseCreationForm()

    if request.method == 'POST':
        if 'add_student' in request.POST:
            student_form = StudentRegistrationForm(request.POST)
            if student_form.is_valid():
                student_form.save()
                return redirect('admin_page')
        elif 'add_lesson' in request.POST:
            lesson_form = LessonCreationForm(request.POST, request.FILES)
            if lesson_form.is_valid():
                lesson_form.save()
                return redirect('admin_page')
        elif 'add_module' in request.POST:
            module_form = ModuleCreationForm(request.POST)
            if module_form.is_valid():
                module_form.save()
                return redirect('admin_page')
        elif 'add_course' in request.POST:
            course_form = CourseCreationForm(request.POST)
            if course_form.is_valid():
                course_form.save()
                return redirect('admin_page')
        elif 'delete_course' in request.POST:
            course_id = request.POST['course_id']
            Course.objects.filter(id=course_id).delete()
            return redirect('admin_page')

    # Получаем всех студентов из модели Student
    students = Student.objects.all()
    lessons = Lesson.objects.all()
    modules = Module.objects.all()
    courses = Course.objects.all()
    quizzes = Quiz.objects.all()  # Получаем список квизов

    context = {
        'student_form': student_form,
        'lesson_form': lesson_form,
        'module_form': module_form,
        'course_form': course_form,
        'students': students,
        'lessons': lessons,
        'modules': modules,
        'courses': courses,
        'quizzes': quizzes,  # Добавляем квизы в контекст
    }
    return render(request, 'courses/admin_page_test.html', context)

@login_required
def student_page(request):
    # Получаем объект Student, связанный с текущим пользователем
    student = get_object_or_404(Student, user=request.user)  # Если студента нет, будет 404 ошибка
    courses = student.courses.all()  # Получаем курсы, к которым записан студент

    if request.method == 'POST':
        course_code = request.POST.get('course_code')
        try:
            course = Course.objects.get(course_code=course_code)
            student.courses.add(course)  # Добавляем курс к студенту
            # Убедитесь, что сохранение не требуется, так как метод add() уже сохраняет
            return redirect('student_page')  # Перенаправляем на страницу студента
        except Course.DoesNotExist:
            # Обработка случая, если курс не найден
            # Например, вы можете добавить сообщение об ошибке
            error_message = "Курс с данным кодом не найден."
            context = {
                'courses': courses,
                'error_message': error_message,
            }
            return render(request, 'courses/student_page.html', context)

    context = {
        'courses': courses,
    }
    return render(request, 'courses/student_page.html', context)
@login_required
def profile_page(request):
    progress = StudentProgress.objects.filter(student=request.user)
    return render(request, 'courses/profile.html', {'progress': progress})

def logout_view(request):
    logout(request)
    return redirect('admin_login')
@login_required
def course_detail(request, course_id):
    # Получаем курс
    course = get_object_or_404(Course, id=course_id)
    current_lesson = None
    quiz_results = {}  # Словарь для хранения результатов квизов по каждому квизу

    # Обработка запроса на сохранение прогресса
    if request.method == 'POST' and 'save_and_continue' in request.POST:
        lesson_id = request.POST.get('lesson_id')
        lesson = get_object_or_404(Lesson, id=lesson_id)
        progress = float(request.POST.get('progress', 0))

        # Получаем или создаем запись прогресса
        progress_record, created = CourseProgress.objects.get_or_create(
            student=request.user.student,
            course=course,
            module=lesson.module,
            lesson=lesson,
        )
        progress_record.progress = progress
        progress_record.save()

        # Редирект на следующий урок
        next_lesson = get_next_lesson(lesson)
        return redirect('lesson_detail', lesson_id=next_lesson.id) if next_lesson else redirect('course_detail', course_id=course.id)

    # Получаем результаты квизов для каждого модуля
    for module in course.modules.all():
        for quiz in module.quizzes.all():
            # Получаем результат для текущего квиза, если он есть
            quiz_result = quiz.quizresult_set.filter(user=request.user).first()
            if quiz_result:
                quiz_results[quiz.id] = quiz_result  # Сохраняем результат по ID квиза

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'current_lesson': current_lesson,
        'quiz_results': quiz_results,  # Передаем результаты квизов по каждому квизу
    })


def get_next_lesson(current_lesson):
    # Получение следующего урока в текущем модуле
    next_lesson = Lesson.objects.filter(module=current_lesson.module, id__gt=current_lesson.id).first()
    return next_lesson
def add_module_to_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    modules = Module.objects.all()  # Получаем все существующие модули

    if request.method == 'POST':
        selected_module_id = request.POST.get('module_id')
        if selected_module_id:
            module = get_object_or_404(Module, id=selected_module_id)
            course.modules.add(module)  # Привязка модуля к курсу
            return redirect('admin_page')  # Возвращаемся на страницу администратора

    return render(request, 'courses/add_module_to_course.html', {'course': course, 'modules': modules})

def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    student.delete()
    return redirect('admin_page')

@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST':
        lesson.delete()
        return redirect('admin_page')  # Предполагается, что у вас есть URL 'admin_page'
    return render(request, 'courses/delete_lesson.html', {'lesson': lesson})

@login_required
def delete_module(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == 'POST':
        module.delete()
        return redirect('admin_page')
    return render(request, 'courses/delete_module.html', {'module': module})


from django.shortcuts import render, redirect, get_object_or_404
from .models import Question, Answer
from .forms import QuestionForm, AnswerForm
from django.forms import modelformset_factory

@login_required

def create_quiz(request):
    AnswerFormSet = modelformset_factory(Answer, form=AnswerForm, extra=4)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        formset = AnswerFormSet(request.POST)

        if question_form.is_valid() and formset.is_valid():
            question = question_form.save()
            answers = formset.save(commit=False)
            for answer in answers:
                answer.question = question
                answer.save()
            return redirect('quiz_list')

    else:
        question_form = QuestionForm()
        formset = AnswerFormSet(queryset=Answer.objects.none())

    return render(request, 'courses/create_quiz.html', {
        'question_form': question_form,
        'formset': formset
    })
from .forms import StudentProfileForm
# профиль студента
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)

    # Обработка POST запроса, если форма отправлена
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()  # Сохраняем изменения
            return redirect('student_profile')
    else:
        form = StudentProfileForm(instance=student)  # Загружаем данные в форму

    return render(request, 'courses/student_profile.html', {'form': form, 'student': student})
@login_required
def quiz_list(request):
    quizzes = Question.objects.all()
    return render(request, 'courses/quiz_list.html', {'quizzes': quizzes})

@login_required

def edit_quiz(request, pk):
    question = get_object_or_404(Question, quiz__id=pk)
    AnswerFormSet = modelformset_factory(Answer, form=AnswerForm, extra=0)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST, instance=question)
        formset = AnswerFormSet(request.POST, queryset=question.answers.all())

        if question_form.is_valid() and formset.is_valid():
            question_form.save()
            formset.save()
            return redirect('admin_page')

    else:
        question_form = QuestionForm(instance=question)
        formset = AnswerFormSet(queryset=question.answers.all())

    return render(request, 'courses/edit_quiz.html', {
        'question_form': question_form,
        'formset': formset
    })


from django.shortcuts import render, redirect
from .forms import QuizForm, QuestionForm, AnswerFormSet
from .models import Quiz


@login_required
def create_quiz(request):
    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)

        if quiz_form.is_valid():
            quiz = quiz_form.save()
            return redirect('add_question', quiz_id=quiz.id)
    else:
        quiz_form = QuizForm()

    return render(request, 'courses/create_quiz.html', {
        'quiz_form': quiz_form,
    })

from django.contrib.auth import get_user_model

User = get_user_model()

def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()  # Удаляет пользователя, а также связанные с ним записи
    return redirect('admin_page')
@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        formset = AnswerFormSet(request.POST)

        if question_form.is_valid() and formset.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()

            answers = formset.save(commit=False)
            for answer in answers:
                answer.question = question
                answer.save()

            return redirect('add_question', quiz_id=quiz_id)  # Для добавления еще одного вопроса
    else:
        question_form = QuestionForm()
        formset = AnswerFormSet(queryset=Answer.objects.none())

    return render(request, 'courses/add_question.html', {
        'question_form': question_form,
        'formset': formset,
        'quiz': quiz,
    })
from .forms import QuizToModuleForm

def bind_quiz_to_module(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == 'POST':
        form = QuizToModuleForm(request.POST)
        if form.is_valid():
            course = form.cleaned_data['course']
            module = form.cleaned_data['module']

            # Привязка квиза к модулю
            module.quizzes.add(quiz)

            return redirect('success')  # Перенаправление после успешного сохранения
    else:
        form = QuizToModuleForm(initial={'quiz': quiz})

    return render(request, 'courses/choose.html', {'form': form, 'quiz': quiz})

def success_view(request):
    return render(request, 'courses/choose.html')


def detach_module(request, course_id, module_id):
    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(Module, id=module_id)

    course.modules.remove(module)

    return redirect('admin_page')  # Замени на правильный URL

def detach_lesson_from_module(request, lesson_id, module_id):
    if request.method == 'POST':
        try:
            module = Module.objects.get(id=module_id)
            lesson = Lesson.objects.get(id=lesson_id)
            module.lessons.remove(lesson)
            return JsonResponse({'success': True, 'module_name': module.title})
        except Module.DoesNotExist or Lesson.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Модуль или урок не найдены'})
    return JsonResponse({'success': False, 'error': 'Некорректный запрос'})


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Проверяем, проходил ли пользователь этот квиз
    if QuizResult.objects.filter(user=request.user, quiz=quiz).exists():
        return render(request, 'courses/quiz_already_complete.html', {'quiz': quiz})

    if request.method == 'POST':
        # Обработка завершения квиза (например, подсчет правильных ответов)
        # Предполагаем, что результаты квиза отправляются через POST
        score = request.POST.get('score')  # Здесь нужно учитывать реальный формат данных
        QuizResult.objects.create(user=request.user, quiz=quiz, score=score)
        return redirect('quiz_success')  # Перенаправление после успешного завершения

    # Отображение квиза
    questions = quiz.questions.all()
    return render(request, 'courses/quiz.html', {'quiz': quiz, 'questions': questions})


from django.http import JsonResponse
from django.http import JsonResponse

from django.utils import timezone


@login_required
def submit_quiz(request, quiz_id):
    if request.method == 'POST':
        quiz = Quiz.objects.get(id=quiz_id)
        correct_answers_count = 0

        # Перебираем все вопросы квиза
        for question in quiz.questions.all():
            # Получаем выбранный пользователем ответ
            selected_answer = request.POST.get(f'question_{question.id}')

            # Находим правильный ответ для этого вопроса
            correct_answer = question.answers.filter(is_correct=True).first()

            # Проверяем, совпадает ли выбранный ответ с правильным
            if selected_answer == str(correct_answer.id):
                correct_answers_count += 1

        # Создаем объект QuizResult с текущей датой и временем
        result = QuizResult(
            user=request.user,
            quiz=quiz,
            score=correct_answers_count,
            date_taken=timezone.now()  # Устанавливаем дату и время прохождения
        )
        result.save()

        # Возвращаем результат в формате JSON
        return JsonResponse({'success': True, 'score': correct_answers_count})

    return JsonResponse({'success': False, 'message': 'Неверный метод запроса.'})


@login_required
def delete_quiz(request, quiz_id):
    if request.method == 'DELETE':
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        quiz.delete()
        return JsonResponse({'message': 'Квиз успешно удален'}, status=200)
    return JsonResponse({'error': 'Неправильный метод'}, status=400)

from django.http import HttpResponseNotFound
@login_required
def quiz_results(request):
    results = QuizResult.objects.filter(user=request.user)
    return render(request, 'courses/quiz_result.html', {'results': results})
@login_required
def delete_course(request, course_id):
    if request.method == 'POST':  # Изменяем метод на POST вместо DELETE
        course = get_object_or_404(Course, id=course_id)
        course.delete()
        return redirect('admin_page')  # Перенаправляем на страницу списка курсов после удаления
    return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@login_required
def create_course(request):
    if request.method == 'POST':
        course_form = CourseCreationForm(request.POST, request.FILES)  # Добавьте request.FILES для загрузки файлов
        if course_form.is_valid():
            course_form.save()
            return redirect('admin_page')  # Перенаправляем на страницу админа
    else:
        course_form = CourseCreationForm()

    courses = Course.objects.all()

    context = {
        'course_form': course_form,
        'courses': courses,
    }
    return render(request, 'courses/create_course.html', context)
@login_required
def module_details(request, module_id):
    module = Module.objects.get(id=module_id)
    lessons = Lesson.objects.filter(module=module)

    context = {
        'module': module,
        'lessons': lessons,
    }
    return render(request, 'courses/module_details.html', context)

def show_lessons(request):
    lessons_title = Lesson.title.objects.all()
    return render(request, 'courses/admin_page_test.html', {'lessons_title': lessons_title})

def get_lessons(request, module_id):
    module = Module.objects.get(id=module_id)
    lessons = module.lessons.all().values('id', 'title')  # Получаем только нужные поля
    return JsonResponse({'lessons': list(lessons)})


def create_module(request):
    if request.method == 'POST':
        module_form = ModuleCreationForm(request.POST)

        if module_form.is_valid():
            module = module_form.save()  # Сохраняем модуль в базе данных
            return redirect('admin_page')  # Перенаправление на страницу администратора (или другую нужную страницу)
    else:
        module_form = ModuleCreationForm()

    return render(request, 'courses/create_module.html', {
        'module_form': module_form,
    })

from django.shortcuts import render, redirect
from .forms import LessonCreationForm


def create_lesson(request, module_id=None):
    if request.method == 'POST':
        lesson_form = LessonCreationForm(request.POST, request.FILES)

        if lesson_form.is_valid():
            lesson = lesson_form.save()
            if module_id:
                module = Module.objects.get(id=module_id)
                module.lessons.add(lesson)
                module.save()
            return redirect('admin_page')
    else:
        lesson_form = LessonCreationForm()

    return render(request, 'courses/create_lesson.html', {
        'lesson_form': lesson_form,
        'module_id': module_id,
    })

def view_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    return render(request, 'courses/view_lesson.html', {'lesson': lesson})

from django.http import HttpResponse

def replace_video(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST' and request.FILES.get('new_video'):
        lesson.video = request.FILES['new_video']
        lesson.save()
        return redirect('view_lesson', lesson_id=lesson.id)
    return HttpResponse("Ошибка при замене видео.", status=400)

def replace_pdf(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.method == 'POST' and request.FILES.get('new_pdf'):
        lesson.pdf = request.FILES['new_pdf']
        lesson.save()
        return redirect('view_lesson', lesson_id=lesson.id)
    return HttpResponse("Ошибка при замене PDF.", status=400)
def student_list(request):
    students = Student.objects.all()  # Получаем всех студентов из базы данных
    context = {
        'students': students  # Передаем студентов в контекст для шаблона
    }
    return render(request, 'courses/admin_page_test.html', context)

from django.shortcuts import render, get_object_or_404

from django.http import Http404
def student_details(request, student_id):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        raise Http404("Student not found")

    # Проверка на роль администратора
    if request.user.is_staff:  # или request.user.is_admin, если вы это определили
        if request.method == 'POST':
            form = StudentProfileForm(request.POST, instance=student)
            if form.is_valid():
                form.save()  # Сохраняем изменения
                return render(request, 'courses/student_detail.html', {'student': student, 'form': form})
        else:
            form = StudentProfileForm(instance=student)
    else:
        form = None  # Студент не может редактировать свою информацию

    # Возвращаем страницу с данными студента и формой, если пользователь администратор
    return render(request, 'courses/student_detail.html', {'student': student, 'form': form})
@login_required
def calculate_score(post_data, quiz):
    """
    Функция для подсчета результата на основе ответов пользователя
    :param post_data: Данные формы (POST) с ответами пользователя
    :param quiz: Текущий квиз, по которому проходит тест
    :return: Итоговый результат (счет)
    """
    score = 0
    total_questions = quiz.questions.count()  # Предполагаем, что квиз имеет связанные вопросы

    # Проходим по каждому вопросу и проверяем, правильный ли ответ
    for question in quiz.questions.all():
        # Ответ, который пользователь отправил для данного вопроса
        user_answer = post_data.get(f'question_{question.id}')

        # Проверяем, совпадает ли ответ с правильным ответом
        if user_answer and user_answer == question.correct_answer:
            score += 1  # Увеличиваем счет на 1 за каждый правильный ответ

    return score
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = request.user.student  # если используешь модель Student

    # Проверяем, проходил ли пользователь этот квиз
    if QuizResult.objects.filter(student=student, quiz=quiz).exists():
        return render(request, 'courses/already_completed.html')  # отображаем сообщение о том, что тест уже пройден

    if request.method == 'POST':
        # логика прохождения квиза и подсчета результатов
        score = calculate_score(request.POST)  # функция для подсчета результата
        QuizResult.objects.create(student=student, quiz=quiz, score=score)
        return redirect('quiz_result', quiz_id=quiz.id)

    return render(request, 'courses/quiz.html', {'quiz': quiz})

from .models import QuizResult
def quiz_result(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = request.user.student
    result = get_object_or_404(QuizResult, student=student, quiz=quiz)

    return render(request, 'courses/quiz_result.html', {'quiz': quiz, 'result': result})

from django.shortcuts import get_object_or_404
@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)  # Это вернет 404, если квиз не найден
    questions = quiz.questions.all()  # Вопросы, связанные с квизом
    return render(request, 'courses/quiz.html', {'quiz': quiz, 'questions': questions})


import json
import logging
from django.shortcuts import render, redirect
from .models import Course, Module, Lesson, Quiz, Question, Answer


from django.shortcuts import render
from .models import Course, Module, Lesson, Quiz, Question, Answer

