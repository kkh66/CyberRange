from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from quiz.models import Quiz
from scenario.models import Scenario
from scenario.models import UserScenario
from tutorial.models import Tutorial
from .models import ScenarioRating, QuizRating, TutorialRating


# This is the idea of the rating app you can base on your idea to change it.
@login_required
def rate_content(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    tutorial = get_object_or_404(Tutorial, scenario=scenario)
    quiz = get_object_or_404(Quiz, scenario=scenario)
    group_id = scenario.groups.first().group.id

    # Check existing ratings
    scenario_rating = ScenarioRating.objects.filter(
        user=request.user,
        scenario=scenario
    ).first()

    tutorial_rating = TutorialRating.objects.filter(
        user=request.user,
        tutorial=tutorial
    ).first()

    quiz_rating = QuizRating.objects.filter(
        user=request.user,
        quiz=quiz
    ).first()

    if scenario_rating and tutorial_rating and quiz_rating:
        messages.info(request, 'You have already rated this scenario.')
        return redirect('scenario:scenario_list', group_id=group_id)

    if request.method == 'POST':
        scenario_rating_value = request.POST.get('scenario_rating')
        scenario_comment = request.POST.get('scenario_comment', '')
        tutorial_rating_value = request.POST.get('tutorial_rating')
        tutorial_comment = request.POST.get('tutorial_comment', '')
        quiz_rating_value = request.POST.get('quiz_rating')
        quiz_comment = request.POST.get('quiz_comment', '')

        # Validate all ratings are provided
        if not all([scenario_rating_value, tutorial_rating_value, quiz_rating_value]):
            messages.error(request, 'Please provide ratings for all components.')
            return redirect('rating:RateContent', scenario_id=scenario_id)

        # Create ratings
        ScenarioRating.objects.update_or_create(
            user=request.user,
            scenario=scenario,
            defaults={
                'rating': scenario_rating_value,
                'comment': scenario_comment
            }
        )

        TutorialRating.objects.update_or_create(
            user=request.user,
            tutorial=tutorial,
            defaults={
                'rating': tutorial_rating_value,
                'comment': tutorial_comment
            }
        )

        QuizRating.objects.update_or_create(
            user=request.user,
            quiz=quiz,
            defaults={
                'rating': quiz_rating_value,
                'comment': quiz_comment
            }
        )

        # Clean up container after successful rating
        user_scenario = UserScenario.objects.filter(
            scenario=scenario,
            user=request.user,
            container_id__isnull=False
        ).order_by('-id').first()

        if user_scenario and user_scenario.container_id:
            try:
                from scenario.utils import DockerManager
                docker_manager = DockerManager()
                docker_manager.remove_container(user_scenario.container_id)
                user_scenario.container_id = None
                user_scenario.port = None
                user_scenario.save()
            except Exception as e:
                print(f"Error removing container after rating: {e}")

        messages.success(request, 'Thank you for your feedback!')
        return redirect('scenario:scenario_list', group_id=group_id)

    context = {
        'scenario': scenario,
        'tutorial': tutorial,
        'quiz': quiz,
        'scenario_rating': scenario_rating,
        'tutorial_rating': tutorial_rating,
        'quiz_rating': quiz_rating,
        'group_id': group_id,
    }
    return render(request, 'ScenarioComplete.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def get_scenario_analytics(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    ratings = ScenarioRating.objects.filter(scenario=scenario)
    distribution = {
        str(i): ratings.filter(rating=i).count()
        for i in range(1, 6)
    }

    stats = ratings.aggregate(
        avg_rating=Avg('rating'),
        total_ratings=Count('id')
    )

    recent_comments = ratings.order_by('-created_at')[:5].values(
        'user__username',
        'rating',
        'comment',
        'created_at'
    )

    analytics = {
        'distribution': distribution,
        'stats': {
            'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0,
            'total_ratings': stats['total_ratings']
        },
        'recent_comments': list(recent_comments)
    }

    return JsonResponse(analytics)


@login_required
@user_passes_test(lambda u: u.is_staff)
def get_tutorial_analytics(request, tutorial_id):
    tutorial = get_object_or_404(Tutorial, id=tutorial_id)

    ratings = TutorialRating.objects.filter(tutorial=tutorial)
    distribution = {
        str(i): ratings.filter(rating=i).count()
        for i in range(1, 6)
    }

    stats = ratings.aggregate(
        avg_rating=Avg('rating'),
        total_ratings=Count('id')
    )

    analytics = {
        'distribution': distribution,
        'stats': {
            'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0,
            'total_ratings': stats['total_ratings']
        }
    }

    return JsonResponse(analytics)


@login_required
def check_completion(request, scenario_id):
    try:
        scenario = get_object_or_404(Scenario, id=scenario_id)
        rating_completed = ScenarioRating.objects.filter(
            user=request.user,
            scenario=scenario
        ).exists()

        return JsonResponse({
            'completed': rating_completed,
            'rating_url': reverse('rating:RateContent', args=[scenario_id]) if not rating_completed else None
        })
    except Exception as e:
        return JsonResponse({
            'completed': False,
            'rating_url': reverse('rating:RateContent', args=[scenario_id]),
            'error': str(e)
        })
