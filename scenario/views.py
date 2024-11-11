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


# CRUD for the Step
@login_required
def manage_steps(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    steps = Step.objects.filter(scenario=scenario).order_by('order')

    if request.method == 'POST':
        step_content = request.POST.get('step_content')
        if step_content:
            max_order = steps.aggregate(models.Max('order'))['order__max']
            next_order = 0 if max_order is None else max_order + 1

            Step.objects.create(
                scenario=scenario,
                step_content=step_content,
                order=next_order
            )
            messages.success(request, 'Step added successfully!')
            return redirect('scenario:manage_steps', scenario_id=scenario_id)

    context = {
        'scenario': scenario,
        'steps': steps
    }
    return render(request, 'Instructor/AddStep.html', context)


@login_required
def delete_step(request, step_id):
    step = get_object_or_404(Step, id=step_id)
    scenario_id = step.scenario.id

    if request.method == 'POST':
        step.delete()
        messages.success(request, 'Step deleted successfully!')

    return redirect('scenario:manage_steps', scenario_id=scenario_id)


@login_required
def edit_step(request, step_id):
    step = get_object_or_404(Step, id=step_id)

    if request.method == 'POST':
        step_content = request.POST.get('step_content')
        step.step_content = step_content
        step.save()
        messages.success(request, 'Step updated successfully!')

    return redirect('scenario:manage_steps', scenario_id=step.scenario.id)


# CRUD for the UserScenario

@login_required
def start_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    docker_manager = DockerManager()

    existing_scenario = UserScenario.objects.filter(
        user=request.user,
        scenario=scenario,
        container_id__isnull=False
    ).first()

    container_name = f"{request.user.username}_{scenario.name}".replace(' ', '_').lower()

    try:
        if existing_scenario:
            try:
                container = docker_manager.client.containers.get(existing_scenario.container_id)
                return redirect('scenario:scenario_detail', scenario_id=scenario_id)
            except docker.errors.NotFound:
                container_id, port = docker_manager.start_container(
                    scenario.docker_name,
                    container_name
                )
                existing_scenario.container_id = container_id
                existing_scenario.port = port
                existing_scenario.save()

                update_user_steps(existing_scenario)

                messages.success(request, f'Scenario restarted successfully! Access it at port {port}')
                return redirect('scenario:scenario_detail', scenario_id=scenario_id)

        container_id, port = docker_manager.start_container(
            scenario.docker_name,
            container_name
        )

        user_scenario = UserScenario.objects.create(
            user=request.user,
            scenario=scenario,
            container_id=container_id,
            port=port
        )

        steps = Step.objects.filter(scenario=scenario).order_by('order')
        for step in steps:
            UserStep.objects.create(
                user_scenario=user_scenario,
                step=step,
                step_done=False
            )

        messages.success(request, f'Scenario started successfully! Access it at port {port}')
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    except Exception as e:
        messages.error(request, f'Failed to start scenario: {str(e)}')
        return redirect('scenario:scenario_list', group_id=scenario.groups.first().group.id)


@login_required
def scenario_detail(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    user_scenario = UserScenario.objects.filter(
        user=request.user,
        scenario=scenario
    ).first()

    if user_scenario:
        if user_scenario.is_time_exceeded and not user_scenario.time_exceeded:
            user_scenario.time_exceeded = True
            user_scenario.save()

    context = {
        'scenario': scenario,
        'user_scenario': user_scenario,
        'group': scenario.groups.first().group,
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
def container_info(request, scenario_id):
    user_scenario = get_object_or_404(
        UserScenario,
        scenario_id=scenario_id,
        user=request.user,
        container_id__isnull=False
    )

    docker_manager = DockerManager()
    try:
        info = docker_manager.get_container_info(user_scenario.container_id)
        return JsonResponse({
            'State': {
                'Status': info.get('State', {}).get('Status', 'unknown'),
                'Running': info.get('State', {}).get('Running', False),
                'Paused': info.get('State', {}).get('Paused', False)
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def complete_step(request, step_id):
    user_step = get_object_or_404(UserStep,
                                  id=step_id,
                                  user_scenario__user=request.user)

    if request.method == 'POST' and user_step.is_current_step:
        user_step.step_done = True
        user_step.save()
        messages.success(request, 'Step completed successfully!')

    return redirect('scenario:scenario_detail',
                    scenario_id=user_step.user_scenario.scenario.id)


@login_required
def add_step(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    if request.method == 'POST':
        step_content = request.POST.get('step_content')
        is_expert = request.POST.get('is_expert', '') == 'on'

        next_order = Step.objects.filter(scenario=scenario).count()

        step = Step.objects.create(
            scenario=scenario,
            step_content=step_content,
            order=next_order,
            is_expert=is_expert
        )

        reorder_steps(scenario)

        messages.success(request, 'Step added successfully!')
    return redirect('scenario:manage_steps', scenario_id=scenario_id)


@login_required
def edit_step(request, scenario_id, step_id):
    step = get_object_or_404(Step, id=step_id, scenario_id=scenario_id)
    if request.method == 'POST':
        step_content = request.POST.get('step_content')
        is_expert = request.POST.get('is_expert') == 'on'

        step.step_content = step_content
        step.is_expert = is_expert
        step.save()

        messages.success(request, 'Step updated successfully!')
    return redirect('scenario:manage_steps', scenario_id=scenario_id)


@login_required
def move_step(request, scenario_id, step_id, direction):
    if request.method == 'POST':
        scenario = get_object_or_404(Scenario, id=scenario_id)
        step = get_object_or_404(Step, id=step_id, scenario=scenario)

        steps = list(Step.objects.filter(scenario=scenario).order_by('order'))
        current_index = steps.index(step)

        if direction == 'up' and current_index > 0:
            previous_step = steps[current_index - 1]
            step.order, previous_step.order = previous_step.order, step.order
            step.save()
            previous_step.save()

            reorder_steps(scenario)

            user_scenarios = UserScenario.objects.filter(scenario=scenario)
            for user_scenario in user_scenarios:
                update_user_steps(user_scenario)

            messages.success(request, 'Step moved up successfully!')

        elif direction == 'down' and current_index < len(steps) - 1:
            next_step = steps[current_index + 1]
            step.order, next_step.order = next_step.order, step.order
            step.save()
            next_step.save()

            reorder_steps(scenario)

            user_scenarios = UserScenario.objects.filter(scenario=scenario)
            for user_scenario in user_scenarios:
                update_user_steps(user_scenario)

            messages.success(request, 'Step moved down successfully!')

    return redirect('scenario:manage_steps', scenario_id=scenario_id)


def reorder_steps(scenario):
    steps = Step.objects.filter(scenario=scenario).order_by('order')
    for index, step in enumerate(steps):
        if step.order != index:
            step.order = index
            step.save()


@login_required
def check_progress(request, scenario_id):
    user_scenario = get_object_or_404(
        UserScenario,
        scenario_id=scenario_id,
        user=request.user,
        container_id__isnull=False
    )

    # Get rating status
    has_rated = ScenarioRating.objects.filter(
        user=request.user,
        scenario_id=scenario_id
    ).exists()

    # Calculate progress
    completed_count = user_scenario.user_steps.filter(step_done=True).count()
    total_count = user_scenario.user_steps.count()

    # Calculate time information
    elapsed_time = (timezone.now() - user_scenario.created_at).total_seconds()
    time_limit_seconds = user_scenario.scenario.time_limit * 60
    time_remaining = max(0, time_limit_seconds - elapsed_time)
    is_time_exceeded = elapsed_time > time_limit_seconds

    # Check if scenario is completed
    if completed_count == total_count:
        return JsonResponse({
            'completed': completed_count,
            'total': total_count,
            'no_steps': False,
            'scenario_completed': True,
            'has_rated': has_rated,
            'completion_url': reverse('scenario:scenario_completion', args=[scenario_id]),
            'list_url': reverse('scenario:scenario_list', args=[user_scenario.scenario.groups.first().group.id]),
            # Add time information
            'elapsed_time': elapsed_time,
            'time_remaining': time_remaining / 60,  # Convert to minutes
            'time_exceeded': is_time_exceeded,
            'time_limit': user_scenario.scenario.time_limit
        })

    # Get current step
    current_step = next(
        (step for step in user_scenario.user_steps.order_by('step__order') if not step.step_done),
        None
    )

    return JsonResponse({
        'completed': completed_count,
        'total': total_count,
        'no_steps': False,
        'current_step': {
            'order': current_step.step.order,
            'content': current_step.step.step_content
        } if current_step else None,
        # Add time information
        'elapsed_time': elapsed_time,
        'time_remaining': time_remaining / 60,  # Convert to minutes
        'time_exceeded': is_time_exceeded,
        'time_limit': user_scenario.scenario.time_limit,
        'start_time': user_scenario.created_at.isoformat()
    })


@login_required
def rate_scenario(request, scenario_id):
    if request.method == 'POST':
        scenario = get_object_or_404(Scenario, id=scenario_id)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')

        rating_obj, created = ScenarioRating.objects.update_or_create(
            user=request.user,
            scenario=scenario,
            defaults={'rating': rating, 'comment': comment}
        )

        messages.success(request, 'Rating submitted successfully!')
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    return redirect('scenario:scenario_detail', scenario_id=scenario_id)


@login_required
def rate_step(request, scenario_id, step_id):
    if request.method == 'POST':
        step = get_object_or_404(Step, id=step_id, scenario_id=scenario_id)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')

        rating_obj, created = StepRating.objects.update_or_create(
            user=request.user,
            step=step,
            defaults={'rating': rating, 'comment': comment}
        )

        messages.success(request, 'Step rating submitted successfully!')
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    return redirect('scenario:scenario_detail', scenario_id=scenario_id)


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
        .order_by('rating'),
        'step_stats': StepRating.objects.filter(step__scenario=scenario)
        .values('step__order', 'step__step_content')
        .annotate(
            avg_rating=Avg('rating'),
            total_ratings=Count('id')
        )
        .order_by('step__order')
    }

    return JsonResponse(analytics)


@login_required
def submit_completion_ratings(request, scenario_id):
    if request.method == 'POST':
        scenario = get_object_or_404(Scenario, id=scenario_id)

        if ScenarioRating.objects.filter(user=request.user, scenario=scenario).exists():
            messages.warning(request, 'You have already rated this scenario.')
            return redirect('scenario:scenario_list', group_id=scenario.groups.first().group.id)

        scenario_rating = request.POST.get('scenario_rating')
        if scenario_rating:
            scenario_comment = request.POST.get('scenario_comment', '')
            ScenarioRating.objects.create(
                user=request.user,
                scenario=scenario,
                rating=scenario_rating,
                comment=scenario_comment
            )

        steps = Step.objects.filter(scenario=scenario)
        for step in steps:
            step_rating = request.POST.get(f'step_{step.id}_rating')
            if step_rating:
                step_comment = request.POST.get(f'step_{step.id}_comment', '')
                StepRating.objects.create(
                    user=request.user,
                    step=step,
                    rating=step_rating,
                    comment=step_comment
                )

        messages.success(request, 'Thank you for your feedback!')
        return redirect('scenario:scenario_list', group_id=scenario.groups.first().group.id)

    return redirect('scenario:scenario_completion', scenario_id=scenario_id)


@login_required
def scenario_completion(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    steps = Step.objects.filter(scenario=scenario).order_by('order')
    group = scenario.groups.first().group

    context = {
        'scenario': scenario,
        'steps': steps,
        'group': group,
    }
    return render(request, 'ScenarioComplete.html', context)


@login_required(login_url='account:login')
def console_view(request):
    context = {}

    if request.user.is_staff:
        total_scenarios = Scenario.objects.count()
        total_users = User.objects.filter(is_staff=False).count()
        completed_scenarios = UserScenario.objects.filter(
            user_steps__step_done=True
        ).distinct().count()
        active_scenarios = UserScenario.objects.filter(
            container_id__isnull=False
        ).count()

        recent_activities = UserStep.objects.select_related(
            'user_scenario__user',
            'user_scenario__scenario'
        ).filter(
            step_done=True
        ).order_by('-user_scenario__created_at')[:10]

        top_scenarios = Scenario.objects.annotate(
            avg_rating=Avg('ratings__rating'),
            total_ratings=Count('ratings')
        ).filter(total_ratings__gt=0).order_by('-avg_rating')[:5]

        context.update({
            'total_scenarios': total_scenarios,
            'total_users': total_users,
            'completed_scenarios': completed_scenarios,
            'active_scenarios': active_scenarios,
            'recent_activities': recent_activities,
            'top_scenarios': top_scenarios,
        })

    return render(request, 'Console.html', context)


def update_user_steps(user_scenario):
    current_steps = Step.objects.filter(scenario=user_scenario.scenario).order_by('order')
    existing_user_steps = UserStep.objects.filter(user_scenario=user_scenario)

    step_status = {us.step_id: us.step_done for us in existing_user_steps}

    existing_user_steps.delete()

    for step in current_steps:
        UserStep.objects.create(
            user_scenario=user_scenario,
            step=step,
            step_done=step_status.get(step.id, False)
        )


@login_required
def test_container(request):
    docker_manager = DockerManager()

    test_scenario = Scenario.objects.filter(name='Testing Use').first()
    if not test_scenario:
        test_scenario = Scenario.objects.create(
            name='Testing Use',
            description='This is a test scenario for chmod detection',
            docker_name='teting_use:latest'
        )
        Step.objects.create(
            scenario=test_scenario,
            step_content='Change file permissions using chmod command',
            order=0
        )

    container_name = f"{request.user.username}_{test_scenario.name}".replace(' ', '_').lower()

    try:
        container_id, port = docker_manager.start_test_container(
            test_scenario.docker_name,
            container_name,
            request.user.id
        )

        user_scenario = UserScenario.objects.create(
            user=request.user,
            scenario=test_scenario,
            container_id=container_id,
            port=port
        )

        step = Step.objects.get(scenario=test_scenario)
        UserStep.objects.create(
            user_scenario=user_scenario,
            step=step,
            step_done=False
        )

        return JsonResponse({
            'status': 'success',
            'container_id': container_id,
            'port': port
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def get_container_logs(request, container_id):
    try:
        docker_manager = DockerManager()
        logs = docker_manager.get_container_logs(container_id)

        if "Command executed: chmod" in logs:
            try:
                user_scenario = UserScenario.objects.get(container_id=container_id)
                user_step = UserStep.objects.get(user_scenario=user_scenario)
                if not user_step.step_done:
                    user_step.step_done = True
                    user_step.save()
            except (UserScenario.DoesNotExist, UserStep.DoesNotExist):
                pass

        return JsonResponse({
            'status': 'success',
            'logs': logs
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

