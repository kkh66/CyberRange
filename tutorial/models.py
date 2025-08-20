from django.db import models
from tinymce.models import HTMLField
from scenario.models import Scenario


class Tutorial(models.Model):
    scenario = models.OneToOneField(Scenario, on_delete=models.CASCADE, related_name='tutorial')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tutorial for {self.scenario.name}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"Tutorial for {self.scenario.name}"
        super().save(*args, **kwargs)


class Section(models.Model):
    tutorial = models.ForeignKey(Tutorial, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    content = HTMLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.tutorial.scenario.name} - {self.title}"


class TutorialImage(models.Model):
    image = models.ImageField(upload_to='tutorial_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    tutorial = models.ForeignKey(Tutorial, on_delete=models.CASCADE, related_name='images')

    def __str__(self):
        return f"Image for {self.tutorial.title} - {self.uploaded_at}"
