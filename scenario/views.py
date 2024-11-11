from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from group.models import Group
from django.contrib import messages
from django.http import JsonResponse

from scenario.models import Scenario, GroupScenario, UserScenario, UserStep, Step
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

        scenario = Scenario.objects.create(
            name=name,
            description=description,
            docker_name=docker_image
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

        scenario.name = name
        scenario.description = description
        scenario.docker_name = docker_image
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


# CRUD for the Step

@login_required
def list_all_scenarios(request):
    # Get filter parameters
    group_id = request.GET.get('group')
    search_query = request.GET.get('search')

    # Base queryset
    group_scenarios = GroupScenario.objects.select_related('group', 'scenario').all()

    # Apply filters
    if group_id:
        group_scenarios = group_scenarios.filter(group_id=group_id)
    if search_query:
        group_scenarios = group_scenarios.filter(scenario__name__icontains=search_query)

    # Get all groups for the filter dropdown
    groups = Group.objects.all()

    context = {
        'group_scenarios': group_scenarios,
        'groups': groups,
        'selected_group': int(group_id) if group_id else None,
        'search_query': search_query,
    }
    return render(request, 'Instructor/ListAllScenario.html', context)


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

    if existing_scenario:
        return redirect('scenario:scenario_detail', scenario_id=scenario_id)

    container_name = f"{request.user.username}_{scenario.name}".replace(' ', '_').lower()

    try:
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
        scenario=scenario,
        container_id__isnull=False
    ).first()

    group_scenario = get_object_or_404(GroupScenario, scenario=scenario)
    group = group_scenario.group

    context = {
        'scenario': scenario,
        'user_scenario': user_scenario,
        'group': group,
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
        return JsonResponse(info)
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
def check_progress(request, scenario_id):
    user_scenario = get_object_or_404(
        UserScenario,
        scenario_id=scenario_id,
        user=request.user,
        container_id__isnull=False
    )

    scenario_steps = Step.objects.filter(scenario=user_scenario.scenario).order_by('order')
    existing_user_steps = UserStep.objects.filter(user_scenario=user_scenario)
    existing_step_ids = set(existing_user_steps.values_list('step_id', flat=True))

    for step in scenario_steps:
        if step.id not in existing_step_ids:
            UserStep.objects.create(
                user_scenario=user_scenario,
                step=step,
                step_done=False
            )

    user_steps = UserStep.objects.filter(
        user_scenario=user_scenario
    ).select_related('step').order_by('step__order')

    total_count = user_steps.count()

    if total_count == 0:
        return JsonResponse({
            'completed': 0,
            'total': 0,
            'no_steps': True
        })

    completed_count = user_steps.filter(step_done=True).count()

    # Get current step info
    current_step = next(
        (step for step in user_steps if not step.step_done),
        None
    )

    return JsonResponse({
        'completed': completed_count,
        'total': total_count,
        'no_steps': False,
        'current_step': {
            'order': current_step.step.order,
            'content': current_step.step.step_content
        } if current_step else None
    })
