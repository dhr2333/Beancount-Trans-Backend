# project/celery.py
import os
from celery import Celery
from django.conf import settings

# 设置默认的Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.develop')

app = Celery('project')  # 创建Celery应用实例
app.config_from_object('django.conf:settings', namespace='CELERY')  # 使用Django的设置文件配置Celery
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'  # 使用数据库调度器
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # 自动从所有已注册的Django应用中加载任务