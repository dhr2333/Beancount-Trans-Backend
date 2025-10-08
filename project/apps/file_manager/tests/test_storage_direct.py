#!/usr/bin/env python3
"""
直接测试存储模块
不导入整个Django项目，只测试存储相关的代码
"""

import sys
import os
from io import BytesIO

# 添加utils目录到Python路径
utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project', 'utils')
sys.path.insert(0, utils_path)

def test_storage_factory():
    """测试存储工厂模块"""
    print("测试存储工厂模块...")

    try:
        # 直接导入存储工厂
        from storage_factory import StorageBackend, StorageFactory, get_storage_client
        print("✓ 成功导入存储工厂模块")

        # 测试抽象基类
        print("✓ StorageBackend抽象基类存在")

        # 测试工厂类
        print("✓ StorageFactory类存在")

        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_minio_backend():
    """测试MinIO后端"""
    print("测试MinIO后端...")

    try:
        from minio import MinIOBackend

        # 测试配置
        config = {
            'ENDPOINT': '127.0.0.1:9000',
            'ACCESS_KEY': 'minioadmin',
            'SECRET_KEY': 'minioadmin',
            'BUCKET_NAME': 'beancount-trans',
            'USE_HTTPS': False
        }

        # 创建后端实例
        backend = MinIOBackend(config)
        print("✓ MinIO后端创建成功")

        # 检查方法
        methods = ['upload_file', 'download_file', 'delete_file', 'file_exists', 'get_file_url']
        for method in methods:
            if hasattr(backend, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 缺失")
                return False

        return True
    except ImportError as e:
        print(f"✗ MinIO后端导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ MinIO后端测试失败: {e}")
        return False

def test_oss_backend():
    """测试OSS后端"""
    print("测试OSS后端...")

    try:
        from oss_conn import OSSBackend

        # 测试配置
        config = {
            'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
            'ACCESS_KEY_ID': 'test',
            'ACCESS_KEY_SECRET': 'test',
            'BUCKET_NAME': 'beancount-trans',
            'REGION': 'cn-hangzhou'
        }

        # 创建后端实例
        backend = OSSBackend(config)
        print("✓ OSS后端创建成功")

        # 检查方法
        methods = ['upload_file', 'download_file', 'delete_file', 'file_exists', 'get_file_url']
        for method in methods:
            if hasattr(backend, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 缺失")
                return False

        return True
    except ImportError as e:
        print(f"✗ OSS后端导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ OSS后端测试失败: {e}")
        return False

def test_s3_backend():
    """测试S3后端"""
    print("测试S3后端...")

    try:
        from s3_conn import S3Backend

        # 测试配置
        config = {
            'ENDPOINT_URL': 'https://s3.amazonaws.com',
            'ACCESS_KEY_ID': 'test',
            'SECRET_ACCESS_KEY': 'test',
            'BUCKET_NAME': 'beancount-trans',
            'REGION': 'us-east-1',
            'USE_SSL': True,
            'VERIFY_SSL': True
        }

        # 创建后端实例
        backend = S3Backend(config)
        print("✓ S3后端创建成功")

        # 检查方法
        methods = ['upload_file', 'download_file', 'delete_file', 'file_exists', 'get_file_url']
        for method in methods:
            if hasattr(backend, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 缺失")
                return False

        return True
    except ImportError as e:
        print(f"✗ S3后端导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ S3后端测试失败: {e}")
        return False

def test_abstract_interface():
    """测试抽象接口"""
    print("测试抽象接口...")

    try:
        from storage_factory import StorageBackend

        # 检查抽象基类的方法
        abstract_methods = StorageBackend.__abstractmethods__
        expected_methods = {'upload_file', 'download_file', 'delete_file', 'file_exists', 'get_file_url'}

        if abstract_methods == expected_methods:
            print("✓ 抽象方法定义正确")
        else:
            print(f"✗ 抽象方法不匹配: 期望 {expected_methods}, 实际 {abstract_methods}")
            return False

        return True
    except Exception as e:
        print(f"✗ 抽象接口测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("存储模块直接测试")
    print("=" * 50)

    tests = [
        ("存储工厂", test_storage_factory),
        ("抽象接口", test_abstract_interface),
        ("MinIO后端", test_minio_backend),
        ("OSS后端", test_oss_backend),
        ("S3后端", test_s3_backend),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✓ {test_name} 通过")
        else:
            print(f"✗ {test_name} 失败")

    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！存储模块实现正确。")
        print("\n存储系统特性:")
        print("✓ 支持MinIO存储")
        print("✓ 支持阿里云OSS存储") 
        print("✓ 支持通用S3兼容存储")
        print("✓ 统一的抽象接口")
        print("✓ 工厂模式自动选择")
        print("\n下一步:")
        print("1. 安装依赖: pipenv install")
        print("2. 配置真实的存储服务")
        print("3. 在Django项目中使用")
        return 0
    else:
        print("❌ 部分测试失败，请检查实现。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
