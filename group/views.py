import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
import json
from group.models import Group, GroupAnnouncement


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
    return render(request, 'ViewGroup.html', {'group': group})


@login_required
def create_announcement(request, group_id):
    if request.method == 'POST' and request.user.is_staff:
        group = get_object_or_404(Group, id=group_id)
        title = request.POST.get('title')
        announcement_text = request.POST.get('announcement')

        if announcement_text:
            GroupAnnouncement.objects.create(
                group=group,
                title=title,
                announcement=announcement_text,
                created_by=request.user
            )
            messages.success(request, 'Announcement posted successfully.')

    return redirect('group:group_detail', group_id=group_id)


@user_passes_test(lambda u: u.is_staff)
def add_students(request, group_id):
    if request.method == 'POST':
        group = get_object_or_404(Group, id=group_id)
        student_emails = request.POST.get('student_emails', '').split()

        added_count = 0
        for email in student_emails:
            try:
                student = User.objects.get(email=email.strip())
                if student not in group.students.all():
                    group.students.add(student)
                    added_count += 1
            except User.DoesNotExist:
                messages.warning(request, f'User with email {email} not found.')

        if added_count > 0:
            messages.success(request, f'Successfully added {added_count} student(s) to the group.')

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



