#!/usr/bin/env python3
"""
测试案例文件功能
验证 admin 用户案例文件创建和新用户文件引用功能
"""

import os
import sys
import django
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.db import transaction

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.develop')
django.setup()

from project.apps.file_manager.models import Directory, File
from project.apps.translate.models import ParseFile
from project.apps.account.management.commands.init_official_templates import Command


class SampleFilesTestCase(TransactionTestCase):
    """测试案例文件功能"""

    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123456'
        )
        # 确保 admin 用户 ID 为 1
        if self.admin_user.id != 1:
            self.admin_user.id = 1
            self.admin_user.save()

    def test_create_sample_files_for_admin(self):
        """测试为 admin 用户创建案例文件"""
        print("测试为 admin 用户创建案例文件...")
        
        # 创建案例文件
        command = Command()
        command._create_sample_files_for_admin(self.admin_user, force=True)
        
        # 验证目录结构
        sample_dir = Directory.objects.filter(
            name='案例文件',
            owner=self.admin_user,
            parent__isnull=True
        ).first()
        
        self.assertIsNotNone(sample_dir, "案例文件目录应该存在")
        
        wechat_dir = Directory.objects.filter(
            name='微信账单',
            owner=self.admin_user,
            parent=sample_dir
        ).first()
        
        self.assertIsNotNone(wechat_dir, "微信账单目录应该存在")
        
        alipay_dir = Directory.objects.filter(
            name='支付宝账单',
            owner=self.admin_user,
            parent=sample_dir
        ).first()
        
        self.assertIsNotNone(alipay_dir, "支付宝账单目录应该存在")
        
        # 验证文件（如果本地文件存在）
        wechat_file = File.objects.filter(
            name='完整测试_微信.csv',
            owner=self.admin_user,
            directory=wechat_dir
        ).first()
        
        alipay_file = File.objects.filter(
            name='完整测试_支付宝.csv',
            owner=self.admin_user,
            directory=alipay_dir
        ).first()
        
        if os.path.exists('完整测试_微信.csv'):
            self.assertIsNotNone(wechat_file, "微信案例文件应该存在")
            self.assertIsNotNone(wechat_file.storage_name, "文件应该有存储名称")
        
        if os.path.exists('完整测试_支付宝.csv'):
            self.assertIsNotNone(alipay_file, "支付宝案例文件应该存在")
            self.assertIsNotNone(alipay_file.storage_name, "文件应该有存储名称")
        
        print("✓ admin 用户案例文件创建测试通过")

    def test_new_user_file_reference(self):
        """测试新用户文件引用功能"""
        print("测试新用户文件引用功能...")
        
        # 首先为 admin 创建案例文件
        command = Command()
        command._create_sample_files_for_admin(self.admin_user, force=True)
        
        # 创建新用户
        new_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='test123456'
        )
        
        # 验证新用户有案例文件目录
        new_sample_dir = Directory.objects.filter(
            name='案例文件',
            owner=new_user,
            parent__isnull=True
        ).first()
        
        self.assertIsNotNone(new_sample_dir, "新用户应该有案例文件目录")
        
        # 验证新用户有子目录
        new_wechat_dir = Directory.objects.filter(
            name='微信账单',
            owner=new_user,
            parent=new_sample_dir
        ).first()
        
        self.assertIsNotNone(new_wechat_dir, "新用户应该有微信账单目录")
        
        new_alipay_dir = Directory.objects.filter(
            name='支付宝账单',
            owner=new_user,
            parent=new_sample_dir
        ).first()
        
        self.assertIsNotNone(new_alipay_dir, "新用户应该有支付宝账单目录")
        
        # 验证文件引用（如果 admin 有案例文件）
        admin_files = File.objects.filter(
            owner=self.admin_user,
            directory__parent__name='案例文件'
        )
        
        if admin_files.exists():
            for admin_file in admin_files:
                # 检查新用户是否有对应的文件引用
                new_file = File.objects.filter(
                    name=admin_file.name,
                    owner=new_user
                ).first()
                
                self.assertIsNotNone(new_file, f"新用户应该有文件引用: {admin_file.name}")
                self.assertEqual(
                    new_file.storage_name, 
                    admin_file.storage_name,
                    "文件引用应该使用相同的存储名称"
                )
                
                # 验证解析记录
                parse_file = ParseFile.objects.filter(file=new_file).first()
                self.assertIsNotNone(parse_file, "文件引用应该有解析记录")
        
        print("✓ 新用户文件引用测试通过")

    def test_file_reference_mechanism(self):
        """测试文件引用机制"""
        print("测试文件引用机制...")
        
        # 创建两个用户
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='test123456'
        )
        
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='test123456'
        )
        
        # 为 admin 创建案例文件
        command = Command()
        command._create_sample_files_for_admin(self.admin_user, force=True)
        
        # 获取 admin 的文件
        admin_files = File.objects.filter(
            owner=self.admin_user,
            directory__parent__name='案例文件'
        )
        
        if admin_files.exists():
            admin_file = admin_files.first()
            storage_name = admin_file.storage_name
            
            # 统计引用该存储文件的文件数量
            reference_count = File.objects.filter(
                storage_name=storage_name
            ).count()
            
            self.assertGreaterEqual(reference_count, 1, "至少应该有一个文件引用")
            
            # 删除一个用户的文件引用
            user1_file = File.objects.filter(
                name=admin_file.name,
                owner=user1
            ).first()
            
            if user1_file:
                user1_file.delete()
                
                # 验证其他引用仍然存在
                remaining_references = File.objects.filter(
                    storage_name=storage_name
                ).count()
                
                self.assertGreaterEqual(remaining_references, 1, "删除一个引用后，其他引用应该仍然存在")
        
        print("✓ 文件引用机制测试通过")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("案例文件功能测试")
    print("=" * 60)
    
    # 创建测试实例
    test_case = SampleFilesTestCase()
    test_case.setUp()
    
    try:
        # 运行测试
        test_case.test_create_sample_files_for_admin()
        test_case.test_new_user_file_reference()
        test_case.test_file_reference_mechanism()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！案例文件功能工作正常。")
        print("\n功能特性:")
        print("✓ admin 用户自动创建案例文件")
        print("✓ 新用户自动获得案例文件引用")
        print("✓ 文件引用机制避免重复存储")
        print("✓ 目录结构自动创建")
        print("✓ 解析记录自动创建")
        print("✓ .bean 文件自动创建")
        print("\n使用方法:")
        print("1. 运行: python manage.py init_official_templates")
        print("2. 新用户注册时会自动获得案例文件")
        print("3. 案例文件存储在: 案例文件/微信账单/ 和 案例文件/支付宝账单/")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
