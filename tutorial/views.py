from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from .models import Tutorial, Section, TutorialImage
from scenario.models import Scenario
import os


@login_required
def view_tutorial(request, scenario_id):
    try:
        scenario = get_object_or_404(Scenario, id=scenario_id)
        tutorial = get_object_or_404(Tutorial, scenario=scenario)
        sections = tutorial.sections.all().order_by('order')

        group_scenario = scenario.groups.select_related('group').first()
        if not group_scenario:
            messages.error(request, "No group associated with this scenario.")
            return redirect('scenario:list_all_scenarios')

        context = {
            'tutorial': tutorial,
            'sections': sections,
            'scenario': scenario,
            'group_id': group_scenario.group.id
        }
        return render(request, 'Tutorial.html', context)
    except Http404:
        messages.error(request, "Tutorial or scenario not found.")
        return redirect('scenario:console')


@user_passes_test(lambda u: u.is_staff)
def create_tutorial(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)

    if hasattr(scenario, 'tutorial'):
        messages.warning(request, 'Tutorial already exists for this scenario.')
        return redirect('tutorial:ListTutorials', scenario_id=scenario_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        try:
            tutorial = Tutorial.objects.create(
                scenario=scenario,
                title=title,
                description=description
            )

            section_titles = request.POST.getlist('section_title')
            section_contents = request.POST.getlist('section_content')

            for i, (title, content) in enumerate(zip(section_titles, section_contents)):
                if title and content:
                    Section.objects.create(
                        tutorial=tutorial,
                        title=title,
                        content=content,
                        order=i
                    )

            messages.success(request, 'Tutorial created successfully!')
            return redirect('tutorial:ListTutorials', scenario_id=scenario_id)
        except Exception as e:
            messages.error(request, f'Failed to create tutorial: {str(e)}')
            return redirect('tutorial:CreateTutorial', scenario_id=scenario_id)

    return render(request, 'Instructor/Tutorial/AddTutorial.html', {
        'scenario': scenario,
    })


@csrf_exempt
@user_passes_test(lambda u: u.is_staff)
def upload_image(request):
    if request.method != 'POST':
        messages.error(request, 'Method not allowed')
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if 'file' not in request.FILES:
        messages.error(request, 'No file was uploaded')
        return JsonResponse({'error': 'No file was uploaded'}, status=400)

    file_obj = request.FILES['file']
    file_name_suffix = file_obj.name.split(".")[-1].lower()
    if file_name_suffix not in ['jpg', 'png', 'gif', 'jpeg']:
        messages.error(request, 'Invalid file format')
        return JsonResponse({'error': 'Invalid file format'}, status=400)

    try:
        path = os.path.join('tutorial_images', file_obj.name)
        path = default_storage.save(path, file_obj)
        file_url = default_storage.url(path)
        messages.success(request, 'Image uploaded successfully')
        return JsonResponse({'location': file_url})
    except Exception as e:
        messages.error(request, f'Failed to upload image: {str(e)}')
        return JsonResponse({'error': 'Failed to upload image'}, status=500)


@login_required
def list_tutorials(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    tutorial = Tutorial.objects.filter(scenario=scenario).first()

    if not tutorial:
        return redirect('tutorial:CreateTutorial', scenario_id=scenario_id)

    return render(request, 'Instructor/Tutorial/ListTutorial.html', {
        'tutorial': tutorial,
        'scenario': scenario
    })


@login_required
@require_POST
def add_section(request):
    try:
        tutorial_id = request.POST.get('tutorial_id')
        title = request.POST.get('title')
        content = request.POST.get('content')

        tutorial = get_object_or_404(Tutorial, id=tutorial_id)
        order = tutorial.sections.count()

        Section.objects.create(
            tutorial=tutorial,
            title=title,
            content=content,
            order=order
        )
        messages.success(request, 'Section added successfully')
        return redirect('tutorial:ListTutorials', scenario_id=tutorial.scenario.id)
    except Exception as e:
        messages.error(request, f'Failed to add section: {str(e)}')
        return redirect('tutorial:ListTutorials', scenario_id=tutorial.scenario.id)


@login_required
@require_POST
def edit_section(request):
    try:
        section_id = request.POST.get('section_id')
        title = request.POST.get('title')
        content = request.POST.get('content')

        section = get_object_or_404(Section, id=section_id)
        section.title = title
        section.content = content
        section.save()

        messages.success(request, 'Section updated successfully')
        return JsonResponse({'status': 'success'})
    except Exception as e:
        messages.error(request, f'Failed to update section: {str(e)}')
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['DELETE'])
def delete_section(request, section_id):
    try:
        section = get_object_or_404(Section, id=section_id)
        section.delete()
        messages.success(request, 'Section deleted successfully')
        return JsonResponse({'status': 'success'})
    except Exception as e:
        messages.error(request, f'Failed to delete section: {str(e)}')
        return JsonResponse({'error': str(e)}, status=400)
