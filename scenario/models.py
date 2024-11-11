from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from .utils import DockerManager


# Create your models here.
class Scenario(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    docker_name = models.CharField(max_length=255)
    time_limit = models.IntegerField(
        default=60,  # Default 60 minutes
        help_text="Time limit in minutes"
    )

    def __str__(self):
        return self.name


class Step(models.Model):
    scenario = models.ForeignKey(Scenario, related_name='steps', on_delete=models.CASCADE)
    step_content = models.TextField()
    order = models.IntegerField(default=0)
    is_expert = models.BooleanField(default=False, verbose_name='Expert Content')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Step {self.order + 1}: {self.step_content}"


class UserScenario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.ForeignKey(Scenario, related_name='user_scenarios', on_delete=models.CASCADE)
    container_id = models.CharField(max_length=255, null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    time_exceeded = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def time_remaining(self):
        if not self.created_at:
            return 0
        
        elapsed = timezone.now() - self.created_at
        limit = timezone.timedelta(minutes=self.scenario.time_limit)
        remaining = limit - elapsed
        
        return max(0, remaining.total_seconds() / 60)

    @property
    def is_time_exceeded(self):
        return self.time_remaining <= 0

    def __str__(self):
        return f"{self.user.username} - {self.scenario.name}"

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


class UserStep(models.Model):
    user_scenario = models.ForeignKey(UserScenario, related_name='user_steps', on_delete=models.CASCADE)
    step = models.ForeignKey(Step, related_name='user_steps', on_delete=models.CASCADE)
    step_done = models.BooleanField(default=False)

    class Meta:
        ordering = ['step__order']

    def __str__(self):
        return f"{self.user_scenario.user.username} - Step {self.step.order + 1}"

    @property
    def is_current_step(self):
        previous_steps = UserStep.objects.filter(
            user_scenario=self.user_scenario,
            step__order__lt=self.step.order
        )
        return (not self.step_done and
                (previous_steps.count() == 0 or
                 previous_steps.filter(step_done=True).count() == previous_steps.count()))


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


class StepRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    step = models.ForeignKey(Step, related_name='ratings', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'step')

    def __str__(self):
        return f"{self.user.username} - Step {self.step.order + 1} - {self.rating} stars"

    @property
    def stars_display(self):
        return '★' * self.rating + '☆' * (5 - self.rating)
