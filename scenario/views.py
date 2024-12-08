from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from group.models import Group
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Max, Subquery, OuterRef
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from scenario.models import *
from .utils import DockerManager
from django.utils import timezone
from quiz.models import Quiz, QuizAttempt
from rating.models import ScenarioRating
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import json


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

        scenario = Scenario.objects.create(
            name=name,
            description=description,
            docker_name=docker_image,
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
        return redirect('scenario:list_all_scenarios')

    return redirect('scenario:list_all_scenarios')


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
@user_passes_test(lambda u: u.is_staff)
def list_all_scenarios(request):
    group_id = request.GET.get('group')
    search_query = request.GET.get('search')

    # Filter group scenarios to only show those from groups created by the current user
    group_scenarios = GroupScenario.objects.select_related('group', 'scenario').filter(
        group__staff=request.user
    )

    if group_id and group_id.isdigit():
        group_scenarios = group_scenarios.filter(group_id=group_id)
    if search_query:
        group_scenarios = group_scenarios.filter(scenario__name__icontains=search_query)

    group_scenarios = group_scenarios.order_by('-created_at')

    # Only show groups created by the current user in the dropdown
    context = {
        'group_scenarios': group_scenarios,
        'groups': Group.objects.filter(staff=request.user).order_by('name'),
        'selected_group': int(group_id) if group_id and group_id.isdigit() else None,
        'search_query': search_query or '',
    }

    return render(request, 'Instructor/ListAllScenario.html', context)


@login_required()
def scenario_description(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    group_scenario = get_object_or_404(GroupScenario, scenario=scenario)

    context = {
        'scenario': scenario,
        'group': group_scenario.group,
    }
    return render(request, 'ScenarioDescription.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def start_scenario(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    # Check if user has completed the scenario
    user_scenario = UserScenario.objects.filter(
        scenario=scenario,
        user=request.user,
        completed_at__isnull=False,
        screenshots__isnull=False
    ).first()

    if user_scenario:
        # Check if quiz exists and is completed
        try:
            quiz = Quiz.objects.get(scenario=scenario)
            quiz_completed = QuizAttempt.objects.filter(
                user=request.user,
                quiz=quiz
            ).exists()

            if not quiz_completed:
                return redirect('quiz:TakeQuiz', scenario_id=scenario_id)
        except Quiz.DoesNotExist:
            quiz_completed = True

        # Check if rating is completed
        rating_completed = ScenarioRating.objects.filter(
            user=request.user,
            scenario=scenario
        ).exists()

        if not rating_completed:
            return redirect('rating:RateContent', scenario_id=scenario_id)

        if quiz_completed and rating_completed:
            messages.info(request, 'You have already completed this scenario.')
            return redirect('scenario:scenario_list', group_id=scenario.groups.first().group.id)

    docker_manager = DockerManager()

    # Get or create user scenario
    user_scenario, created = UserScenario.objects.get_or_create(
        scenario=scenario,
        user=request.user,
        completed_at__isnull=True,
        defaults={'container_id': None, 'port': None}
    )

    try:
        # Check if container exists and is running
        if user_scenario.container_id:
            try:
                status = docker_manager.get_container_status(user_scenario.container_id)
                if status['status'] == 'success' and status['container_status']['is_running']:
                    # Container is running, redirect to detail page
                    messages.info(request, 'Scenario is already running')
                    return redirect('scenario:scenario_detail', scenario_id=scenario_id)
                else:
                    # Container exists but not running, clean it up
                    try:
                        docker_manager.start_container(user_scenario.container_id)
                    except Exception as e:
                        print(f"Error cleaning up non-running container: {e}")
            except Exception as e:
                print(f"Error checking container status: {e}")
                # Container likely doesn't exist anymore, clean up reference
                user_scenario.container_id = None
                user_scenario.port = None
                user_scenario.save()

        # Start new container
        container_name = f"{request.user.username}_{scenario.name}".replace(' ', '_').lower()
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

    has_completed = UserScenario.objects.filter(
        scenario=scenario,
        user=request.user,
        completed_at__isnull=False,
        screenshots__isnull=False
    ).exists()

    context = {
        'scenario': scenario,
        'group': group_scenario.group,
        'user_scenario': user_scenario,
        'has_completed': has_completed,
    }
    return render(request, 'ScenarioDetail.html', context)


@login_required
def container_action(request, scenario_id):
    if request.method == 'POST':
        action = request.POST.get('action')
        user_scenario = get_object_or_404(
            UserScenario.objects.filter(
                scenario_id=scenario_id,
                user=request.user
            ).order_by('-id')[:1]
        )

        docker_manager = DockerManager()
        try:
            if action == 'start':
                if not user_scenario.container_id:
                    container_name = f"{request.user.username}_{user_scenario.scenario.name}".replace(' ', '_').lower()
                    container_id, port = docker_manager.start_container(
                        user_scenario.scenario.docker_name,
                        container_name
                    )
                    user_scenario.container_id = container_id
                    user_scenario.port = port
                    user_scenario.save()
                    messages.success(request, 'Container started successfully')
                else:
                    # Check if container actually exists and is running
                    try:
                        status = docker_manager.get_container_status(user_scenario.container_id)
                        if status['status'] == 'error' or not status['container_status']['is_running']:
                            # Container doesn't exist or isn't running, start a new one
                            container_name = f"{request.user.username}_{user_scenario.scenario.name}".replace(' ',
                                                                                                              '_').lower()
                            container_id, port = docker_manager.start_container(
                                user_scenario.scenario.docker_name,
                                container_name
                            )
                            user_scenario.container_id = container_id
                            user_scenario.port = port
                            user_scenario.save()
                            messages.success(request, 'Container started successfully')
                        else:
                            messages.info(request, 'Container is already running')
                    except Exception as e:
                        messages.error(request, f'Error checking container status: {str(e)}')
                        user_scenario.container_id = None
                        user_scenario.port = None
                        user_scenario.save()

            elif action == 'restart':
                try:
                    if user_scenario.container_id:
                        docker_manager.restart_container(user_scenario.container_id)
                    else:
                        container_name = f"{request.user.username}_{user_scenario.scenario.name}".replace(' ',
                                                                                                          '_').lower()
                        container_id, port = docker_manager.start_container(
                            user_scenario.scenario.docker_name,
                            container_name
                        )
                        user_scenario.container_id = container_id
                        user_scenario.port = port
                    user_scenario.save()
                    messages.success(request, 'Container restarted successfully')
                except Exception as e:
                    messages.error(request, str(e))
                    user_scenario.container_id = None
                    user_scenario.port = None
                    user_scenario.save()

            elif action == 'stop':
                if not user_scenario.container_id:
                    messages.info(request, "Container is already stopped")
                else:
                    try:
                        docker_manager.stop_container(user_scenario.container_id)
                        user_scenario.container_id = None
                        user_scenario.port = None
                        user_scenario.save()
                        messages.success(request, 'Container stopped successfully')
                    except Exception as e:
                        messages.error(request, str(e))

            elif action == 'pause':
                if not user_scenario.container_id:
                    messages.error(request, "Container is not running")
                else:
                    docker_manager.pause_container(user_scenario.container_id)
                    messages.success(request, 'Container paused successfully')

            elif action == 'unpause':
                if not user_scenario.container_id:
                    messages.error(request, "Container is not running")
                else:
                    docker_manager.unpause_container(user_scenario.container_id)
                    messages.success(request, 'Container resumed successfully')

        except Exception as e:
            error_message = str(e)
            messages.error(request, error_message)
            if action in ['restart', 'start']:
                user_scenario.container_id = None
                user_scenario.port = None
                user_scenario.save()

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

        if not user_scenario:
            return JsonResponse({
                'status': 'success',
                'container_status': {
                    'status': 'stopped',
                    'is_paused': False,
                    'is_running': False,
                    'started_at': None,
                    'runtime': 0
                },
                'progress_info': {
                    'progress': 0,
                    'level': None,
                    'logs': ''
                },
                'quiz_url': reverse('quiz:TakeQuiz', args=[scenario_id]) if has_quiz else None
            })

        if user_scenario.container_id and user_scenario.port:
            docker_manager = DockerManager()
            try:
                status_info = docker_manager.get_container_status(user_scenario.container_id)

                if status_info['status'] == 'success':
                    current_progress = status_info['progress_info']['progress']

                    if status_info['container_status']['is_paused']:
                        status_info['container_status']['status'] = 'paused'
                    elif current_progress >= 100 and status_info['container_status']['status'] == 'running':
                        status_info['container_status']['status'] = 'completed'
                    elif status_info['container_status']['is_running']:
                        status_info['container_status']['status'] = 'running'

                    return JsonResponse(status_info)

            except Exception as docker_error:
                print(f"Docker error: {docker_error}")
                return JsonResponse({
                    'status': 'success',
                    'container_status': {
                        'status': 'running',
                        'is_paused': False,
                        'is_running': True,
                        'started_at': None,
                        'runtime': 0
                    },
                    'progress_info': {
                        'progress': 0,
                        'level': None,
                        'logs': str(docker_error)
                    },
                    'quiz_url': reverse('quiz:TakeQuiz', args=[scenario_id]) if has_quiz else None
                })

        return JsonResponse({
            'status': 'success',
            'container_status': {
                'status': 'stopped',
                'is_paused': False,
                'is_running': False,
                'started_at': None,
                'runtime': 0
            },
            'progress_info': {
                'progress': 0,
                'level': None,
                'logs': ''
            },
            'quiz_url': reverse('quiz:TakeQuiz', args=[scenario_id]) if has_quiz else None
        })

    except Exception as e:
        print(f"General error: {e}")
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


@login_required(login_url='account:login')
def console(request):
    if request.user.is_staff:
        # Get instructor's groups
        instructor_groups = Group.objects.filter(staff=request.user)

        # Admin dashboard data
        total_users = instructor_groups.aggregate(
            total_students=Count('students', distinct=True)
        )['total_students'] or 0

        # Get all scenarios from instructor's groups
        group_scenarios = GroupScenario.objects.filter(
            group__in=instructor_groups
        ).select_related('group', 'scenario')

        total_scenarios = group_scenarios.count()
        total_groups = instructor_groups.count()

        # Get active student scenarios from instructor's groups
        active_student_scenarios = UserScenario.objects.filter(
            scenario__groups__group__in=instructor_groups,  # Scenario must be in instructor's group
            user__joined_group__in=instructor_groups,  # Student must be in instructor's group
            completed_at__isnull=True,
            container_id__isnull=False
        ).select_related(
            'user',
            'scenario'
        ).distinct().order_by('-id')

        # Get container progress for active scenarios
        docker_manager = DockerManager()
        for user_scenario in active_student_scenarios:
            try:
                status_info = docker_manager.get_container_status(user_scenario.container_id)
                if status_info['status'] == 'success':
                    user_scenario.progress = status_info['progress_info']['progress']
                else:
                    user_scenario.progress = 0
            except Exception:
                user_scenario.progress = 0

        # Get pending approvals for scenarios in instructor's groups
        pending_approvals = UserScenario.objects.filter(
            scenario__groups__group__in=instructor_groups,  # Scenario must be in instructor's group
            user__joined_group__in=instructor_groups,  # Student must be in instructor's group
            approval_status='pending',  # Must be pending
            completed_at__isnull=False,  # Must be completed
            screenshots__isnull=False  # Must have screenshots
        ).select_related(
            'user',
            'scenario'
        ).prefetch_related(
            'screenshots'
        ).distinct()

        # Check each condition separately
        all_user_scenarios = UserScenario.objects.all()

        scenarios_in_groups = all_user_scenarios.filter(
            scenario__groups__group__in=instructor_groups
        )

        users_in_groups = all_user_scenarios.filter(
            user__joined_group__in=instructor_groups
        )

        pending_status = all_user_scenarios.filter(
            approval_status='pending'
        )

        completed = all_user_scenarios.filter(
            completed_at__isnull=False
        )

        with_screenshots = all_user_scenarios.filter(
            screenshots__isnull=False
        )

        pending_approvals = pending_approvals.order_by('-completed_at')

        # Get completed scenarios
        completed_scenarios = UserScenario.objects.filter(
            scenario__groups__group__in=instructor_groups,  # Scenario must be in instructor's group
            user__joined_group__in=instructor_groups,  # Student must be in instructor's group
            completed_at__isnull=False,  # Must be completed
            screenshots__isnull=False  # Must have screenshots
        ).select_related(
            'user',
            'scenario',
            'approved_by'
        ).prefetch_related(
            'screenshots',
            'scenario__groups'  # Prefetch group relationships
        ).annotate(
            quiz_score=Subquery(
                QuizAttempt.objects.filter(
                    user=OuterRef('user'),
                    quiz__scenario=OuterRef('scenario')
                ).order_by('-completed_at').values('score')[:1]
            ),
            total_questions=Subquery(
                QuizAttempt.objects.filter(
                    user=OuterRef('user'),
                    quiz__scenario=OuterRef('scenario')
                ).order_by('-completed_at').values('total_questions')[:1]
            ),
            rating=Subquery(
                ScenarioRating.objects.filter(
                    user=OuterRef('user'),
                    scenario=OuterRef('scenario')
                ).values('rating')[:1]
            )
        ).distinct().order_by('-completed_at')

        context = {
            'total_users': total_users,
            'total_scenarios': total_scenarios,
            'total_groups': total_groups,
            'active_student_scenarios': active_student_scenarios,
            'pending_approvals': pending_approvals,
            'completed_scenarios': completed_scenarios
        }
    else:
        # Student dashboard data
        user_scenarios = UserScenario.objects.filter(
            user=request.user
        ).select_related('scenario').prefetch_related(
            'scenario__groups'
        ).order_by('-scenario__groups__created_at')

        total_scenarios = user_scenarios.count()
        completed_scenarios = user_scenarios.filter(completed_at__isnull=False).count()
        total_groups = Group.objects.filter(students=request.user).count()

        avg_score = QuizAttempt.objects.filter(
            user=request.user
        ).aggregate(
            avg_score=models.Avg(models.F('score') * 100.0 / models.F('total_questions'))
        )['avg_score'] or 0

        context = {
            'user_scenarios': user_scenarios,
            'total_scenarios': total_scenarios,
            'completed_scenarios': completed_scenarios,
            'total_groups': total_groups,
            'avg_score': round(avg_score, 1)
        }

    return render(request, 'Console.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def approve_scenario(request, scenario_id, user_id):
    if request.method == 'POST':
        user_scenario = get_object_or_404(
            UserScenario,
            scenario_id=scenario_id,
            user_id=user_id
        )
        action = request.POST.get('action')

        if action == 'approve':
            user_scenario.approval_status = 'approved'
            user_scenario.approved_at = timezone.now()
            user_scenario.approved_by = request.user
            messages.success(request, 'Scenario completion approved successfully.')
        elif action == 'reject':
            user_scenario.approval_status = 'rejected'
            messages.warning(request, 'Scenario completion rejected.')
        elif action == 'pending':
            user_scenario.approval_status = 'pending'
            user_scenario.approved_at = None
            user_scenario.approved_by = None
            messages.info(request, 'Scenario status set to pending.')

        user_scenario.save()

    return redirect('scenario:console')


@login_required
def submit_screenshots(request, scenario_id):
    if request.method == 'POST':
        try:
            scenario = get_object_or_404(Scenario, id=scenario_id)
            user_scenario = UserScenario.objects.filter(
                scenario=scenario,
                user=request.user
            ).order_by('-id').first()

            files = request.FILES.getlist('screenshots[]')

            if not files:
                return JsonResponse({
                    'success': False,
                    'message': 'No screenshots provided'
                })

            for screenshot in files:
                if not screenshot.content_type.startswith('image/'):
                    return JsonResponse({
                        'success': False,
                        'message': f'Invalid file type: {screenshot.content_type}'
                    })

                ScenarioScreenshot.objects.create(
                    user_scenario=user_scenario,
                    image=screenshot
                )

            user_scenario.completed_at = timezone.now()
            user_scenario.approval_status = 'pending'
            user_scenario.save()

            quiz_url = reverse('quiz:TakeQuiz', args=[scenario_id])

            return JsonResponse({
                'success': True,
                'message': 'Screenshots submitted successfully. Take the quiz while waiting for instructor approval.',
                'quiz_url': quiz_url
            })

        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_scenario_description(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    scenario_details = ScenarioDetails.objects.filter(scenario=scenario).first()
    levels = Level.objects.filter(scenario=scenario).order_by('id')

    if request.method == 'POST':
        try:
            # Create or update scenario details
            if scenario_details:
                scenario_details.description = request.POST.get('description', '')
                scenario_details.objectives = request.POST.get('objectives', '')
                scenario_details.prerequisites = request.POST.get('prerequisites', '')
                scenario_details.objective_detail = request.POST.get('objective_detail', '')
                scenario_details.save()
            else:
                scenario_details = ScenarioDetails.objects.create(
                    scenario=scenario,
                    description=request.POST.get('description', ''),
                    objectives=request.POST.get('objectives', ''),
                    prerequisites=request.POST.get('prerequisites', ''),
                    objective_detail=request.POST.get('objective_detail', '')
                )

            # Handle levels
            existing_level_ids = set()
            level_data = {}

            # Collect level data from POST
            for key, value in request.POST.items():
                if key.startswith('level_'):
                    parts = key.split('_')
                    if len(parts) >= 3:  # level_1_difficulty
                        level_id = parts[1]
                        field = parts[2]  # Get the field name (difficulty, mode, etc.)

                        if level_id not in level_data:
                            level_data[level_id] = {}
                        level_data[level_id][field] = value

            # Create or update levels
            for level_id, data in level_data.items():
                try:
                    if level_id.isdigit() and Level.objects.filter(id=level_id, scenario=scenario).exists():
                        level = Level.objects.get(id=level_id)
                        existing_level_ids.add(level.id)
                    else:
                        level = Level(scenario=scenario)

                    # Update level fields
                    level.difficulty = data.get('difficulty', 'beginner')
                    level.mode = data.get('mode', 'singleplayer')
                    level.tools = data.get('tools', '')
                    try:
                        level.recommended_time = int(data.get('time', 0))
                    except (ValueError, TypeError):
                        level.recommended_time = 0

                    level.save()

                    if level.id:
                        existing_level_ids.add(level.id)
                except Exception as e:
                    messages.error(request, f'Error processing level {level_id}: {str(e)}')

            # Delete removed levels
            Level.objects.filter(scenario=scenario).exclude(id__in=existing_level_ids).delete()

            messages.success(request, 'Scenario details and levels updated successfully!')
            return redirect('scenario:ScenarioAddDescription', scenario_id=scenario.id)

        except Exception as e:
            messages.error(request, f'Error saving scenario details: {str(e)}')
            return redirect('scenario:ScenarioAddDescription', scenario_id=scenario.id)

    context = {
        'scenario': scenario,
        'scenario_details': scenario_details,
        'levels': levels,
        'difficulty_choices': Level.DIFFICULTY_CHOICES,
        'mode_choices': Level.MODE_CHOICES
    }

    return render(request, 'Instructor/AddScenarioDetails.html', context)
