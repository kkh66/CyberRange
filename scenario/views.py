from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from group.models import Group
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.contrib.auth.decorators import user_passes_test
import docker
from django.urls import reverse
from scenario.models import *
from .utils import DockerManager
from django.utils import timezone
from quiz.models import Quiz


# CRUD of the Scenario.
@login_required
def scenario_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    group_scenarios = GroupScenario.objects.select_related('group', 'scenario').filter(
        group_id=group_id
    ).order_by('-created_at')

    context = {
        'group': group,
        'group_scenarios': group_scenarios,
    }
    return render(request, 'Scenario.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def create_scenario(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        docker_image = request.POST.get('docker_image')
        time_limit = request.POST.get('time_limit', 60)

        scenario = Scenario.objects.create(
            name=name,
            description=description,
            docker_name=docker_image,
            time_limit=time_limit
        )

        GroupScenario.objects.create(group=group, scenario=scenario)
        messages.success(request, 'Scenario created successfully!')
        return redirect('group:group_detail', group_id=group_id)

    return render(request, 'Instructor/AddScenario.html', {'group': group})


@login_required
def edit_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    group_scenario = get_object_or_404(GroupScenario, scenario=scenario)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        docker_image = request.POST.get('docker_image')
        time_limit = request.POST.get('time_limit', 60)

        scenario.name = name
        scenario.description = description
        scenario.docker_name = docker_image
        scenario.time_limit = time_limit
        scenario.save()

        messages.success(request, 'Scenario updated successfully!')
        return redirect('scenario:scenario_list', group_id=group_scenario.group.id)

    return redirect('scenario:scenario_list', group_id=group_scenario.group.id)


@login_required
def delete_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    group_scenario = get_object_or_404(GroupScenario, scenario=scenario)
    group_id = group_scenario.group.id

    if request.method == 'POST':
        scenario.delete()
        messages.success(request, 'Scenario deleted successfully!')

    return redirect('scenario:list_all_scenarios')


@login_required
def list_all_scenarios(request):
    group_id = request.GET.get('group')
    search_query = request.GET.get('search')

    group_scenarios = GroupScenario.objects.select_related('group', 'scenario').all()

    if group_id:
        group_scenarios = group_scenarios.filter(group_id=group_id)
    if search_query:
        group_scenarios = group_scenarios.filter(scenario__name__icontains=search_query)

    groups = Group.objects.all()

    context = {
        'group_scenarios': group_scenarios,
        'groups': groups,
        'selected_group': int(group_id) if group_id else None,
        'search_query': search_query,
    }
    return render(request, 'Instructor/ListAllScenario.html', context)


# CRUD for the UserScenario
@login_required
def start_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    docker_manager = DockerManager()

    old_scenarios = UserScenario.objects.filter(
        scenario=scenario,
        user=request.user,
        container_id__isnull=False
    )
    
    for old_scenario in old_scenarios:
        try:
            if old_scenario.container_id:
                docker_manager.stop_container(old_scenario.container_id)
                docker_manager.remove_container(old_scenario.container_id)
            old_scenario.container_id = None
            old_scenario.completed_at = timezone.now()
            old_scenario.save()
        except Exception as e:
            print(f"Error cleaning up old scenario: {e}")

    # 创建新的 UserScenario
    user_scenario = UserScenario.objects.create(
        user=request.user,
        scenario=scenario
    )

    container_name = f"{request.user.username}_{scenario.name}".replace(' ', '_').lower()

    try:
        container_id, port = docker_manager.start_container(
            scenario.docker_name,
            container_name
        )

        user_scenario.container_id = container_id
        user_scenario.port = port
        user_scenario.save()

        messages.success(request, f'Scenario started successfully! Access it at port {port}')
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    except Exception as e:
        messages.error(request, f'Failed to start scenario: {str(e)}')
        return redirect('scenario:scenario_list', group_id=scenario.groups.first().group.id)


@login_required
def scenario_detail(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    group_scenario = get_object_or_404(GroupScenario, scenario=scenario)
    user_scenario = UserScenario.objects.filter(
        scenario=scenario,
        user=request.user
    ).order_by('-id').first()

    context = {
        'scenario': scenario,
        'group': group_scenario.group,
        'user_scenario': user_scenario,
    }
    return render(request, 'ScenarioDetail.html', context)


@login_required
def container_action(request, scenario_id):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_scenario = get_object_or_404(
            UserScenario,
            scenario_id=scenario_id,
            user=request.user,
            container_id__isnull=False
        )

        docker_manager = DockerManager()
        try:
            if action == 'pause':
                docker_manager.pause_container(user_scenario.container_id)
                messages.success(request, 'Container paused successfully')
            elif action == 'unpause':
                docker_manager.unpause_container(user_scenario.container_id)
                messages.success(request, 'Container resumed successfully')
            elif action == 'restart':
                docker_manager.restart_container(user_scenario.container_id)
                messages.success(request, 'Container restarted successfully')
            elif action == 'stop':
                docker_manager.stop_container(user_scenario.container_id)
                user_scenario.container_id = None
                user_scenario.port = None
                user_scenario.save()
                messages.success(request, 'Container stopped successfully')
        except Exception as e:
            error_message = str(e)
            if "already paused" in error_message:
                messages.error(request, "Container is already paused")
            elif "not paused" in error_message:
                messages.error(request, "Container is not paused")
            elif "is running" in error_message:
                messages.error(request, "Container is already running")
            elif "not running" in error_message:
                messages.error(request, "Container is not running")
            else:
                messages.error(request, f"Failed to {action} container")

    return redirect('scenario:scenario_detail', scenario_id=scenario_id)


@login_required
def get_container_status(request, scenario_id):
    try:
        scenario = get_object_or_404(Scenario, id=scenario_id)
        has_quiz = Quiz.objects.filter(scenario=scenario).exists()
        
        user_scenario = UserScenario.objects.filter(
            scenario=scenario, 
            user=request.user
        ).order_by('-id').first()

        if not user_scenario or not user_scenario.container_id:
            return JsonResponse({
                'status': 'success',
                'container_status': {
                    'status': 'completed',
                    'is_paused': False,
                    'is_running': False,
                    'started_at': None,
                    'runtime': 0
                },
                'progress_info': {
                    'progress': 100,
                    'level': None,
                    'logs': ''
                },
                'quiz_url': reverse('quiz:TakeQuiz', args=[scenario_id]) if has_quiz else None
            })

        docker_manager = DockerManager()
        status_info = docker_manager.get_container_status(user_scenario.container_id)
        
        if 'quiz_url' not in status_info:
            status_info['quiz_url'] = None
            
        if status_info['status'] == 'success' and status_info['progress_info']['progress'] >= 100:
            if has_quiz:
                status_info['quiz_url'] = reverse('quiz:TakeQuiz', args=[scenario_id])
                
        return JsonResponse(status_info)
            
    except Exception as e:
        print(f"Error in get_container_status: {str(e)}")
        return JsonResponse({
            'status': 'success',
            'container_status': {
                'status': 'error',
                'is_paused': False,
                'is_running': False,
                'started_at': None,
                'runtime': 0
            },
            'progress_info': {
                'progress': 0,
                'level': None,
                'logs': str(e)
            },
            'quiz_url': None
        })


@login_required
def rate_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    group = scenario.groups.first().group

    if request.method == 'POST':
        if ScenarioRating.objects.filter(user=request.user, scenario=scenario).exists():
            messages.warning(request, 'You have already rated this scenario.')
            return redirect('scenario:scenario_list', group_id=group.id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')

        if rating:
            ScenarioRating.objects.create(
                user=request.user,
                scenario=scenario,
                rating=rating,
                comment=comment
            )
            messages.success(request, 'Thank you for your feedback!')
        
        return redirect('scenario:scenario_list', group_id=group.id)

    context = {
        'scenario': scenario,
        'group': group,
    }
    return render(request, 'ScenarioComplete.html', context)


@user_passes_test(lambda u: u.is_staff)
def rating_analytics(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    analytics = {
        'scenario_stats': ScenarioRating.objects.filter(scenario=scenario).aggregate(
            avg_rating=Avg('rating'),
            total_ratings=Count('id')
        ),
        'rating_distribution': ScenarioRating.objects.filter(scenario=scenario)
        .values('rating')
        .annotate(count=Count('id'))
        .order_by('rating')
    }

    return JsonResponse(analytics)


@login_required
def console_view(request):
    context = {}

    if request.user.is_staff:
        total_scenarios = Scenario.objects.count()
        total_users = User.objects.filter(is_staff=False).count()
        active_scenarios = UserScenario.objects.filter(
            container_id__isnull=False
        ).count()

        top_scenarios = Scenario.objects.annotate(
            avg_rating=Avg('ratings__rating'),
            total_ratings=Count('ratings')
        ).filter(total_ratings__gt=0).order_by('-avg_rating')[:5]

        context.update({
            'total_scenarios': total_scenarios,
            'total_users': total_users,
            'top_scenarios': top_scenarios,
        })

    return render(request, 'Console.html', context)
