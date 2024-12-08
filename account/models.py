from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pin = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        return timezone.now() < self.expires_at and not self.used


class UserActivationPin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pin = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at


class StaffActivationPin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pin = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at


class LoginAttempt(models.Model):
    MAX_ATTEMPTS = 3  # Easy to modify max attempts in one place
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @classmethod
    def get_failed_attempts(cls, user):
        return cls.objects.filter(user=user).count()
    
    @classmethod
    def clear_attempts(cls, user):
        cls.objects.filter(user=user).delete()
        
    @classmethod
    def add_failed_attempt(cls, user):
        cls.objects.create(user=user)
