"""
pytest配置文件
确保Django设置正确配置
"""
import os
import sys
import django
from pathlib import Path

# 强制设置Django环境变量（必须在任何Django导入之前）
os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings.test'

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 配置Django设置
if not django.conf.settings.configured:
    django.setup()