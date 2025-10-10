#!/usr/bin/env python
"""
系统状态检查脚本
快速检查系统关键组件状态

使用方法：
  # 从项目根目录运行
  python bin/check_system_status.py
  
  # 在容器中运行
  docker exec <container_id> python bin/check_system_status.py
"""
import os
import sys
from pathlib import Path

# 确保能找到项目根目录
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

# 将项目根目录添加到 Python 路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 切换工作目录到项目根
os.chdir(project_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.develop')
django.setup()

from django.contrib.auth import get_user_model
from project.apps.account.models import Account, AccountTemplate
from project.apps.maps.models import Expense, Assets, Income, Template
from project.apps.translate.models import FormatConfig

User = get_user_model()


def main():
    print("\n" + "=" * 60)
    print("Beancount-Trans 系统状态")
    print("=" * 60 + "\n")
    
    # 检查 admin 用户
    try:
        admin = User.objects.get(id=1)
        print(f"✓ 默认用户: {admin.username}")
    except User.DoesNotExist:
        print("✗ 默认用户（id=1）不存在")
        print("  → 运行: python manage.py init_official_templates")
        return
    
    # 统计数据
    print(f"\n【官方模板】")
    print(f"  账户模板: {AccountTemplate.objects.filter(is_official=True).count()} 个")
    print(f"  映射模板: {Template.objects.filter(is_official=True).count()} 个")
    
    print(f"\n【admin 用户数据】")
    print(f"  账户: {Account.objects.filter(owner=admin).count()}")
    print(f"  支出映射: {Expense.objects.filter(owner=admin).count()}")
    print(f"  资产映射: {Assets.objects.filter(owner=admin).count()}")
    print(f"  收入映射: {Income.objects.filter(owner=admin).count()}")
    config = FormatConfig.objects.filter(owner=admin).first()
    print(f"  格式化配置: {config.ai_model if config else 'N/A'}")
    
    print(f"\n【所有用户统计】")
    print(f"  总用户数: {User.objects.count()}")
    print(f"  活跃用户: {User.objects.filter(is_active=True).count()}")
    
    print(f"\n【数据库统计】")
    print(f"  总账户数: {Account.objects.count()}")
    print(f"  总映射数: {Expense.objects.count() + Assets.objects.count() + Income.objects.count()}")
    
    print("\n" + "=" * 60)
    print("系统状态正常")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

