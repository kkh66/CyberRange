from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, Question, QuizAttempt
from scenario.models import Scenario
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from scenario.utils import DockerManager
from scenario.models import UserScenario
from django.http import JsonResponse
from django.urls import reverse


# Quiz CRUD
@login_required
def create_quiz(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    if hasattr(scenario, 'quiz'):
        messages.warning(request, 'A quiz already exists for this scenario.')
        return redirect('quiz:ListQuiz', scenario_id=scenario.id)

    if request.method == 'POST':
        try:
            quiz = Quiz.objects.create(
                scenario=scenario,
                title=request.POST.get('title')
            )

            questions_data = request.POST.items()
            for key, value in questions_data:
                if key.startswith('questions[') and key.endswith('][question_text]'):
                    q_num = key.split('[')[1].split(']')[0]
                    print(f"Creating question {q_num}")
                    Question.objects.create(
                        quiz=quiz,
                        question_text=request.POST.get(f'questions[{q_num}][question_text]'),
                        option_a=request.POST.get(f'questions[{q_num}][option_a]'),
                        option_b=request.POST.get(f'questions[{q_num}][option_b]'),
                        option_c=request.POST.get(f'questions[{q_num}][option_c]'),
                        option_d=request.POST.get(f'questions[{q_num}][option_d]'),
                        correct_option=request.POST.get(f'questions[{q_num}][correct_option]')
                    )

            messages.success(request, 'Quiz created successfully!')
            return redirect('quiz:ListQuiz', scenario_id=scenario.id)

        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')
            return redirect('quiz:ListQuiz', scenario_id=scenario.id)

    return render(request, 'Instructor/quiz/AddQuiz.html', {
        'scenario': scenario
    })


@login_required
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
def quiz_delete(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    quiz = get_object_or_404(Quiz, scenario=scenario)
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully!')
    return redirect('quiz:ListQuiz', scenario_id=scenario_id)


# View Tutorial
def list_tutorial(request):
    return render(request, 'Tutorial.html')


@login_required
def take_quiz(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    quiz = get_object_or_404(Quiz, scenario=scenario)

    if request.method == 'POST':
        try:
            score = int(request.POST.get('score', 0))
            total_questions = int(request.POST.get('total_questions', 0))

            QuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=score,
                total_questions=total_questions
            )

            user_scenario = UserScenario.objects.filter(
                scenario=scenario,
                user=request.user
            ).order_by('-id').first()

            if user_scenario and user_scenario.container_id:
                docker_manager = DockerManager()
                try:
                    docker_manager.stop_container(user_scenario.container_id)
                    docker_manager.remove_container(user_scenario.container_id)
                    user_scenario.container_id = None
                    user_scenario.completed_at = timezone.now()
                    user_scenario.save()
                except Exception as e:
                    print(f"Error cleaning up container: {e}")

            group_scenario = scenario.groups.first()
            if group_scenario:
                group_id = group_scenario.group.id
                list_url = reverse('scenario:scenario_list', args=[group_id])
            else:
                list_url = reverse('scenario:list_all_scenarios')

            return JsonResponse({
                'status': 'success',
                'message': 'Quiz completed successfully!',
                'scenario_id': scenario_id,
                'rate_url': reverse('scenario:rate_scenario', args=[scenario_id]),
                'list_url': list_url
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    questions = quiz.questions.all()
    questions_data = []
    for q in questions:
        questions_data.append({
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'correct_option': q.correct_option
        })

    return render(request, 'Quiz.html', {
        'quiz': quiz,
        'questions': json.dumps(questions_data),
        'scenario': scenario
    })


@login_required
def edit_quiz(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    quiz = get_object_or_404(Quiz, scenario=scenario)

    if request.method == 'POST':
        try:
            # Update quiz title
            quiz.title = request.POST.get('title')
            quiz.save()

            # Delete existing questions
            quiz.questions.all().delete()

            # Create new questions
            questions_data = request.POST.items()
            for key, value in questions_data:
                if key.startswith('questions[') and key.endswith('][question_text]'):
                    q_num = key.split('[')[1].split(']')[0]
                    Question.objects.create(
                        quiz=quiz,
                        question_text=request.POST.get(f'questions[{q_num}][question_text]'),
                        option_a=request.POST.get(f'questions[{q_num}][option_a]'),
                        option_b=request.POST.get(f'questions[{q_num}][option_b]'),
                        option_c=request.POST.get(f'questions[{q_num}][option_c]'),
                        option_d=request.POST.get(f'questions[{q_num}][option_d]'),
                        correct_option=request.POST.get(f'questions[{q_num}][correct_option]')
                    )

            messages.success(request, 'Quiz updated successfully!')
            return redirect('quiz:ListQuiz', scenario_id=scenario.id)

        except Exception as e:
            messages.error(request, f'Error updating quiz: {str(e)}')
            return redirect('quiz:EditQuiz', scenario_id=scenario.id)

    return render(request, 'Instructor/quiz/EditQuiz.html', {
        'quiz': quiz,
        'scenario': scenario
    })
