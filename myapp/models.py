import django
from django.db import models


# Create your models here.


class Users(models.Model):
    name = models.CharField(max_length=32)
    age = models.IntegerField(default=20)
    phone = models.CharField(max_length=16)
    # addtime = models.DateTimeField(default=datetime.now())
    addtime = models.DateTimeField(default=django.utils.timezone.now)

    def __str__(self):
        return self.name


class Department(models.Model):
    title = models.CharField(max_length=16)
