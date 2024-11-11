import os
from django.contrib.auth.models import User
from django.db import models

from CyberRange.utils import generate_classcode


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

    def __str__(self):
        return f"{self.title or 'Announcement'} - {self.announcement[:50]}..."


class AnnouncementAttachment(models.Model):
    announcement = models.ForeignKey(GroupAnnouncement, on_delete=models.CASCADE, related_name='attachments')
    pdf_file = models.FileField(upload_to='announcements/pdfs/')
    file_type = models.CharField(max_length=10, blank=True)

    def save(self, *args, **kwargs):
        # Set file type on save
        file_extension = os.path.splitext(self.pdf_file.name)[1].lower()
        self.file_type = file_extension
        super().save(*args, **kwargs)

    def filename(self):
        return os.path.basename(self.pdf_file.name)


class AnnouncementLink(models.Model):
    announcement = models.ForeignKey(GroupAnnouncement, on_delete=models.CASCADE, related_name='links')
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    favicon = models.URLField(max_length=500, blank=True)
    domain = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.domain})"

    class Meta:
        ordering = ['-created_at']
