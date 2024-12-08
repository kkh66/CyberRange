import random
import json

from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, Question, QuizAttempt
from scenario.models import Scenario, UserScenario
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse


def create_question(quiz, question_data, q_num):
    return Question.objects.create(
        quiz=quiz,
        question_text=question_data.get(f'questions[{q_num}][question_text]'),
        option_a=question_data.get(f'questions[{q_num}][option_a]'),
        option_b=question_data.get(f'questions[{q_num}][option_b]'),
        option_c=question_data.get(f'questions[{q_num}][option_c]'),
        option_d=question_data.get(f'questions[{q_num}][option_d]'),
        correct_option=question_data.get(f'questions[{q_num}][correct_option]')
    )


def process_questions(quiz, post_data):
    questions_data = post_data.items()
    for key, _ in questions_data:
        if key.startswith('questions[') and key.endswith('][question_text]'):
            q_num = key.split('[')[1].split(']')[0]
            create_question(quiz, post_data, q_num)


@login_required
@user_passes_test(lambda u: u.is_staff)
def create_quiz(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    if hasattr(scenario, 'quiz'):
        return redirect('quiz:ListQuiz', scenario_id=scenario.id)

    if request.method == 'POST':
        try:
            quiz = Quiz.objects.create(
                scenario=scenario,
                title=request.POST.get('title', f'Quiz for {scenario.name}')
            )
            process_questions(quiz, request.POST)
            messages.success(request, 'Quiz created successfully!')
            return redirect('quiz:ListQuiz', scenario_id=scenario.id)

        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')
            return redirect('quiz:CreateQuiz', scenario_id=scenario.id)

    return render(request, 'Instructor/quiz/AddQuiz.html', {
        'scenario': scenario
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_list(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    try:
        quiz = Quiz.objects.get(scenario=scenario)
    except Quiz.DoesNotExist:
        quiz = None

    return render(request, 'Instructor/quiz/ListQuizz.html', {
        'quiz': quiz,
        'scenario': scenario
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def quiz_delete(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    quiz = get_object_or_404(Quiz, scenario=scenario)
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully!')
    return redirect('quiz:ListQuiz', scenario_id=scenario_id)


@login_required
def take_quiz(request, scenario_id):
    quiz = get_object_or_404(Quiz, scenario_id=scenario_id)

    existing_attempt = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz
    ).first()

    if existing_attempt:
        messages.info(request, 'You have already completed this quiz.')
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    questions = []
    all_questions = list(quiz.questions.all())
    random.shuffle(all_questions)

    for q in all_questions:
        questions.append({
            'question_text': q.question_text,
            'answers': [q.option_a, q.option_b, q.option_c, q.option_d],
            'correct_answer': getattr(q, f'option_{q.correct_option.lower()}')
        })

    context = {
        'scenario': quiz.scenario,
        'quiz': quiz,
        'questions': questions,
        'urls': {
            'SubmitQuiz': reverse('quiz:SubmitQuiz', args=[scenario_id]),
            'rate_scenario': reverse('rating:RateContent', args=[scenario_id]),
            'scenario_detail': reverse('scenario:scenario_detail', args=[scenario_id])
        }
    }
    return render(request, 'Quiz.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_quiz(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    quiz = get_object_or_404(Quiz, scenario=scenario)

    if request.method == 'POST':
        try:
            quiz.title = request.POST.get('title')
            quiz.save()
            quiz.questions.all().delete()
            process_questions(quiz, request.POST)
            messages.success(request, 'Quiz updated successfully!')
            return redirect('quiz:ListQuiz', scenario_id=scenario.id)

        except Exception as e:
            messages.error(request, f'Error updating quiz: {str(e)}')
            return redirect('quiz:EditQuiz', scenario_id=scenario.id)

    return render(request, 'Instructor/quiz/EditQuiz.html', {
        'quiz': quiz,
        'scenario': scenario
    })


@login_required
def submit_quiz(request, scenario_id):
    if request.method == 'POST':
        try:
            quiz = get_object_or_404(Quiz, scenario_id=scenario_id)

            existing_attempt = QuizAttempt.objects.filter(
                user=request.user,
                quiz=quiz
            ).first()

            if existing_attempt:
                return JsonResponse({
                    'success': False,
                    'message': 'You have already submitted this quiz.'
                }, status=400)

            data = json.loads(request.body)
            score = data.get('score')
            total_questions = data.get('total_questions')

            # Create quiz attempt
            QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=score,
                total_questions=total_questions
            )

            user_scenario = UserScenario.objects.filter(
                scenario_id=scenario_id,
                user=request.user,
                container_id__isnull=False
            ).order_by('-id').first()

            if user_scenario and user_scenario.container_id:
                try:
                    from scenario.utils import DockerManager
                    docker_manager = DockerManager()
                    docker_manager.stop_container(user_scenario.container_id)
                except Exception as e:
                    print(f"Error stopping container: {e}")

            return JsonResponse({
                'success': True,
                'message': 'Quiz submitted successfully'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)


@login_required
def check_completion(request, scenario_id):
    try:
        quiz = get_object_or_404(Quiz, scenario_id=scenario_id)
        quiz_attempt = QuizAttempt.objects.filter(
            user=request.user,
            quiz=quiz
        ).exists()

        return JsonResponse({
            'completed': quiz_attempt,
            'quiz_url': reverse('quiz:TakeQuiz', args=[scenario_id]) if not quiz_attempt else None
        })
    except Quiz.DoesNotExist:
        return JsonResponse({
            'completed': True,
            'quiz_url': None
        })
