from django.db import models
from django.contrib.auth.models import User
from scenario.models import Scenario
from quiz.models import Quiz
from tutorial.models import Tutorial


class BaseRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def stars_display(self):
        return '★' * self.rating + '☆' * (5 - self.rating)


class ScenarioRating(BaseRating):
    scenario = models.ForeignKey(Scenario, related_name='ratings', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'scenario')

    def __str__(self):
        return f"{self.user.username} - {self.scenario.name} - {self.rating} stars"


class QuizRating(BaseRating):
    quiz = models.ForeignKey(Quiz, related_name='ratings', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'quiz')

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.rating} stars"


class TutorialRating(BaseRating):
    tutorial = models.ForeignKey(Tutorial, related_name='ratings', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'tutorial')

    def __str__(self):
        return f"{self.user.username} - {self.tutorial.title} - {self.rating} stars"
