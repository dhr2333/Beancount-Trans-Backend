from django.db import models


# Create your models here.
class File(models.Model):
    name = models.CharField(max_length=32)
    age = models.IntegerField(default=20)
    file_path = models.CharField(max_length=128)


class MyCmodel(models.Model):
    image = models.ImageField(upload_to="images/")


class Expense_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False)
    payee = models.CharField(max_length=8)
    expend = models.CharField(max_length=64, default="Expenses:Other", null=False)
    tag = models.CharField(max_length=16)
    classification = models.CharField(max_length=16)


class Assets_Map(models.Model):
    key = models.CharField(max_length=16, unique=True, null=False)
    full = models.CharField(max_length=16, null=False)
    income = models.CharField(max_length=64, default="Income:Other", null=False)
