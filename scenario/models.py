from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField

from .utils import DockerManager
from django.core.validators import MinValueValidator


# Create your models here.
class Scenario(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    docker_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class UserScenario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    container_id = models.CharField(max_length=100, null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_scenarios'
    )

    class Meta:
        unique_together = ('user', 'scenario')

    @property
    def is_time_exceeded(self):
        if not self.container_id:
            return False

        try:
            docker_manager = DockerManager()
            container_info = docker_manager.get_container_status(self.container_id)
            start_time = container_info.get('StartedAt')
            if not start_time:
                return False

            start_time = timezone.datetime.strptime(
                start_time.split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            ).replace(tzinfo=timezone.utc)

            elapsed = timezone.now() - start_time
            return elapsed.total_seconds() / 60 > self.scenario.time_limit
        except Exception:
            return False

    def clean_up(self):
        if self.container_id:
            try:
                docker_manager = DockerManager()
                docker_manager.stop_container(self.container_id)
            except Exception:
                pass

    def delete(self, *args, **kwargs):
        self.clean_up()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.scenario.name}"


class GroupScenario(models.Model):
    group = models.ForeignKey('group.Group', related_name='scenarios', on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, related_name='groups', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'scenario')

    def __str__(self):
        return f"{self.group.name} - {self.scenario.name}"


class ScenarioScreenshot(models.Model):
    user_scenario = models.ForeignKey(UserScenario, on_delete=models.CASCADE, related_name='screenshots')
    image = models.ImageField(upload_to='scenario_screenshots/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']


class ScenarioDetails(models.Model):
    scenario = models.OneToOneField(Scenario, on_delete=models.CASCADE)
    description = HTMLField(help_text='Main scenario description')
    objectives = HTMLField(help_text='Learning objectives and outcomes')
    prerequisites = HTMLField(help_text='Required prerequisites')
    objective_detail = HTMLField(help_text='Detailed scenario objectives')

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = f"Details for {self.scenario.name}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Details for {self.scenario.name}"


class Level(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    MODE_CHOICES = [
        ('singleplayer', 'Single Player'),
        ('multiplayer', 'Multi Player')
    ]

    scenario = models.OneToOneField(Scenario, on_delete=models.CASCADE, related_name='level')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='singleplayer')
    tools = models.TextField(help_text='Required tools for this level')
    recommended_time = models.IntegerField(help_text='Time in minutes')

    def __str__(self):
        return f"{self.scenario.name} - {self.get_difficulty_display()} Level"

    class Meta:
        ordering = ['id']

