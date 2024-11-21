from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from .utils import DockerManager
from django.core.validators import MinValueValidator


# Create your models here.
class Scenario(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    docker_name = models.CharField(max_length=255)
    time_limit = models.IntegerField(
        default=60,
        validators=[
            MinValueValidator(1, message="The minimum time limit is 1 minute.")]
    )

    def __str__(self):
        return self.name


class UserScenario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, related_name='user_scenarios', on_delete=models.CASCADE)
    container_id = models.CharField(max_length=255, null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('expert', 'Expert')
        ],
        null=True,
        blank=True
    )

    @property
    def is_time_exceeded(self):
        if not self.container_id:
            return False

        try:
            docker_manager = DockerManager()
            container_info = docker_manager.get_container_logs(self.container_id)
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


class ScenarioRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, related_name='ratings', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'scenario')

    def __str__(self):
        return f"{self.user.username} - {self.scenario.name} - {self.rating} stars"

    @property
    def stars_display(self):
        return '★' * self.rating + '☆' * (5 - self.rating)
