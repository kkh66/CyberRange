import os
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError

from CyberRange.utils import generate_classcode


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # Get the file extension
    valid_extensions = ['.pdf', '.txt']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Only PDF and TXT files are allowed.')


# Create your models here.
class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    code = models.CharField(max_length=6, unique=True, blank=True, null=True)
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group')
    students = models.ManyToManyField(User, related_name='joined_group')

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_classcode()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GroupAnnouncement(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200, blank=True)
    announcement = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='announcements/attachment/', null=True, blank=True, max_length=255)

    def __str__(self):
        return f"{self.title or 'Announcement'} - {self.announcement[:50]}..."
    
    def filename(self):
        return os.path.basename(self.attachment.name) if self.attachment else None

    def get_file_type(self):
        if self.attachment:
            ext = os.path.splitext(self.attachment.name)[1].lower()
            return ext[1:]  # Remove the dot
        return None



