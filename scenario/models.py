from django.contrib.auth.models import User
from django.db import models
from .utils import DockerManager


# Create your models here.
class Scenario(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    docker_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Step(models.Model):
    scenario = models.ForeignKey(Scenario, related_name='steps', on_delete=models.CASCADE)
    step_content = models.TextField()
    order = models.IntegerField(default=0)

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
