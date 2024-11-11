import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
import json
<<<<<<< HEAD
from group.models import Group, GroupAnnouncement, AnnouncementAttachment, AnnouncementLink
from django.db import transaction
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
=======
from group.models import Group, GroupAnnouncement, AnnouncementAttachment
from django.db import transaction
>>>>>>> dev


# Create your views here.
@login_required
def group_list(request):
    if request.user.is_staff:
        # Staff can only see groups they created or joined
        groups = Group.objects.filter(
            Q(staff=request.user) |  # Groups they created
            Q(students=request.user)  # Groups they joined
        ).distinct()
    else:
        # Students can only see groups they're enrolled in
        groups = Group.objects.filter(students=request.user)

    return render(request, 'Group.html', {'groups': groups})


@user_passes_test(lambda u: u.is_staff)
def create_group(request):
    if request.method == 'POST':
        name = request.POST.get('group_name')
        description = request.POST.get('group_description')

        if name and description:
            Group.objects.create(
                name=name,
                description=description,
                staff=request.user
            )
            return redirect('group:group_list')

    return redirect('group:group_list')


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    announcements = group.announcements.all().order_by('-created_at')
    return render(request, 'ViewGroup.html', {
        'group': group,
        'announcements': announcements
    })


@login_required
def create_announcement(request, group_id):
    if request.method == 'POST' and request.user.is_staff:
        group = get_object_or_404(Group, id=group_id)
        title = request.POST.get('title')
        announcement_text = request.POST.get('announcement')
        files = request.FILES.getlist('pdf_file')
<<<<<<< HEAD
        links = json.loads(request.POST.get('links', '[]'))  # 获取链接数据
=======
>>>>>>> dev

        if announcement_text:
            with transaction.atomic():
                announcement = GroupAnnouncement.objects.create(
                    group=group,
                    title=title,
                    announcement=announcement_text,
                    created_by=request.user
                )
<<<<<<< HEAD

                # 处理文件上传
                for file in files:
                    file_extension = os.path.splitext(file.name)[1].lower()
=======
                
                for file in files:
                    # Get file extension
                    file_extension = os.path.splitext(file.name)[1].lower()
                    
                    # Check if file type is allowed
>>>>>>> dev
                    if file_extension == '.pdf' and file.content_type == 'application/pdf':
                        AnnouncementAttachment.objects.create(
                            announcement=announcement,
                            pdf_file=file
                        )
                    elif file_extension == '.txt' and file.content_type == 'text/plain':
                        AnnouncementAttachment.objects.create(
                            announcement=announcement,
                            pdf_file=file
                        )
                    else:
                        messages.error(request, 'Only PDF and TXT files are allowed.')
                        announcement.delete()
                        return redirect('group:group_detail', group_id=group_id)
<<<<<<< HEAD

                for link_data in links:
                    AnnouncementLink.objects.create(
                        announcement=announcement,
                        url=link_data['url'],
                        title=link_data['title'],
                        description=link_data.get('description', ''),
                        favicon=link_data.get('favicon', ''),
                        domain=link_data['domain']
                    )

=======
                        
>>>>>>> dev
            messages.success(request, 'Announcement posted successfully.')
        else:
            messages.error(request, 'Please provide an announcement text.')

    return redirect('group:group_detail', group_id=group_id)


@user_passes_test(lambda u: u.is_staff)
def add_students(request, group_id):
    if request.method == 'POST':
        group = get_object_or_404(Group, id=group_id)
        student_ids = request.POST.getlist('student_ids', [])

        added_count = 0
        for student_id in student_ids:
            try:
                student = User.objects.get(
                    id=student_id,
                    is_staff=False,
                    is_superuser=False
                )
                if student not in group.students.all():
                    group.students.add(student)
                    added_count += 1
            except User.DoesNotExist:
                continue

        if added_count > 0:
            messages.success(request, f'Successfully added {added_count} student(s) to the group.')
        else:
            messages.warning(request, 'No new students were added to the group.')

    return redirect('group:group_detail', group_id=group_id)


@user_passes_test(lambda u: u.is_staff)
def remove_student(request, group_id, student_id):
    if request.method == 'POST':
        group = get_object_or_404(Group, id=group_id)
        student = get_object_or_404(User, id=student_id)

        if student in group.students.all():
            group.students.remove(student)
            messages.success(request, f'Successfully removed {student.username} from the group.')

    return redirect('group:group_detail', group_id=group_id)


@login_required
def add_group(request):
    if request.method == 'POST':
        group_code = request.POST.get('group_code')
        try:
            group = Group.objects.get(code=group_code)
            if request.user not in group.students.all():
                group.students.add(request.user)
                messages.success(request, f'You have successfully joined the group: {group.name}.')
            else:
                messages.warning(request, 'You are already a member of this group.')
        except Group.DoesNotExist:
            messages.error(request, 'Invalid group code. Please try again.')

    return redirect('group:group_list')


@user_passes_test(lambda u: u.is_staff)
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if request.method == 'POST':
        name = request.POST.get('group_name')
        description = request.POST.get('group_description')

        if name and description:
            group.name = name
            group.description = description
            group.save()
            messages.success(request, 'Group details updated successfully.')

    return redirect('group:group_detail', group_id=group_id)


@user_passes_test(lambda u: u.is_staff)
def search_students(request, group_id):
    search_term = request.GET.get('term', '')
    group = get_object_or_404(Group, id=group_id)

    students = User.objects.filter(
        Q(username__icontains=search_term) |
        Q(email__icontains=search_term),
        is_staff=False,
        is_superuser=False
    ).exclude(
        id__in=group.students.all()
    )[:10]

    results = [{
        'id': student.id,
        'text': f"{student.username} ({student.email})",
        'username': student.username,
        'email': student.email
    } for student in students]

    return JsonResponse({
        'results': results,
        'pagination': {
            'more': False
        }
    })


def get_link_info(request):
    url = request.GET.get('url')
    if not url:
        return JsonResponse({'error': 'URL is required'}, status=400)
    
    try:
        # 发送请求获取页面内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取网站信息
        og_title = soup.find('meta', property='og:title')
        twitter_title = soup.find('meta', property='twitter:title')
        
        title = ''
        if og_title and og_title.get('content'):
            title = og_title.get('content')
        elif twitter_title and twitter_title.get('content'):
            title = twitter_title.get('content')
        elif soup.title:
            title = soup.title.string
        title = title.strip() if title else ''
        
        # 获取描述
        og_desc = soup.find('meta', property='og:description')
        twitter_desc = soup.find('meta', property='twitter:description')
        meta_desc = soup.find('meta', {'name': 'description'})
        
        description = ''
        if og_desc and og_desc.get('content'):
            description = og_desc.get('content')
        elif twitter_desc and twitter_desc.get('content'):
            description = twitter_desc.get('content')
        elif meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content')
        description = description.strip() if description else ''
        
        # 获取网站域名
        domain = urlparse(url).netloc
        
        # 获取favicon
        icon = soup.find('link', rel='icon')
        shortcut_icon = soup.find('link', rel='shortcut icon')
        
        favicon = ''
        if icon and icon.get('href'):
            favicon = icon.get('href')
        elif shortcut_icon and shortcut_icon.get('href'):
            favicon = shortcut_icon.get('href')
        else:
            favicon = f"{urlparse(url).scheme}://{domain}/favicon.ico"
        
        # 处理相对路径的favicon
        if favicon and not favicon.startswith(('http://', 'https://')):
            if favicon.startswith('//'):
                favicon = f"https:{favicon}"
            elif favicon.startswith('/'):
                favicon = f"{urlparse(url).scheme}://{domain}{favicon}"
            else:
                favicon = f"{urlparse(url).scheme}://{domain}/{favicon}"
        
        return JsonResponse({
            'title': title,
            'description': description,
            'domain': domain,
            'favicon': favicon
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)