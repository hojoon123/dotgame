# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    gold = models.IntegerField(default=1000)
    crystal = models.IntegerField(default=10)

    def __str__(self):
        return self.username
