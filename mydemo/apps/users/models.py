from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')

    class Meta:  # 数据库表名 及 admin站点显示的名称
        db_table = "auth_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name
