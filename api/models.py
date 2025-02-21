from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

# Create your models here.
class CustomUser(AbstractUser):
    uuid = models.UUIDField(primary_key=True, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=[("admin", "Admin"), ("member", "Member")], default="member")

    def __str__(self):
        return self.username