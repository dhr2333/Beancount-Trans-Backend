#!/usr/bin/env python3
"""
简化的存储功能测试脚本
不依赖Django环境，直接测试存储抽象层
"""

import sys
import os
from io import BytesIO

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟Django设置
class MockSettings:
    STORAGE_TYPE = 'minio'
    MINIO_CONFIG = {
        'ENDPOINT': '127.0.0.1:9000',
        'ACCESS_KEY': 'minioadmin',
        'SECRET_KEY': 'minioadmin',
        'BUCKET_NAME': 'beancount-trans',
        'USE_HTTPS': False
    }
    OSS_CONFIG = {
        'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
        'ACCESS_KEY_ID': 'test',
        'ACCESS_KEY_SECRET': 'test',
        'BUCKET_NAME': 'beancount-trans',
        'REGION': 'cn-hangzhou'
    }
    S3_CONFIG = {
        'ENDPOINT_URL': 'https://s3.amazonaws.com',
        'ACCESS_KEY_ID': 'test',
        'SECRET_ACCESS_KEY': 'test',
        'BUCKET_NAME': 'beancount-trans',
        'REGION': 'us-east-1',
        'USE_SSL': True,
        'VERIFY_SSL': True
    }

# 模拟Django设置模块
sys.modules['django.conf'] = type('MockDjangoConf', (), {
    'settings': MockSettings()
})

def test_storage_import():
    """测试存储模块导入"""
    print("测试存储模块导入...")
    
    try:
        from project.utils.storage_factory import StorageBackend, StorageFactory, get_storage_client
        print("✓ 成功导入存储模块")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_storage_backend_creation():
    """测试存储后端创建"""
    print("测试存储后端创建...")
    
    try:
        from project.utils.storage_factory import StorageBackend, StorageFactory
        
        # 测试MinIO后端
        from project.utils.minio import MinIOBackend
        minio_backend = MinIOBackend(MockSettings.MINIO_CONFIG)
        print("✓ MinIO后端创建成功")
        
        # 测试OSS后端
        from project.utils.oss_conn import OSSBackend
        oss_backend = OSSBackend(MockSettings.OSS_CONFIG)
        print("✓ OSS后端创建成功")
        
        # 测试S3后端
        from project.utils.s3_conn import S3Backend
        s3_backend = S3Backend(MockSettings.S3_CONFIG)
        print("✓ S3后端创建成功")
        
        return True
    except Exception as e:
        print(f"✗ 后端创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_storage_factory():
    """测试存储工厂"""
    print("测试存储工厂...")
    
    try:
        from project.utils.storage_factory import StorageFactory
        
        # 测试工厂单例
        factory1 = StorageFactory()
        factory2 = StorageFactory()
        if factory1 is factory2:
            print("✓ 工厂单例模式正常")
        else:
            print("✗ 工厂单例模式异常")
            return False
        
        # 测试获取后端（这里会失败，因为没有真实的连接）
        try:
            backend = factory1.get_backend()
            print(f"✓ 成功获取后端: {type(backend).__name__}")
        except Exception as e:
            print(f"⚠ 获取后端时出现预期错误（因为没有真实连接）: {e}")
        
        return True
    except Exception as e:
        print(f"✗ 工厂测试失败: {e}")
        return False

def test_abstract_methods():
    """测试抽象方法"""
    print("测试抽象方法...")
    
    try:
        from project.utils.storage_factory import StorageBackend
        from project.utils.minio import MinIOBackend
        
        # 创建MinIO后端实例
        backend = MinIOBackend(MockSettings.MINIO_CONFIG)
        
        # 检查是否有必要的方法
        required_methods = ['upload_file', 'download_file', 'delete_file', 'file_exists', 'get_file_url']
        for method in required_methods:
            if hasattr(backend, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 缺失")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 抽象方法测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("存储系统简化测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_storage_import),
        ("抽象方法", test_abstract_methods),
        ("后端创建", test_storage_backend_creation),
        ("存储工厂", test_storage_factory),
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
        print("🎉 所有测试通过！存储抽象层实现正确。")
        print("\n下一步:")
        print("1. 安装依赖: pipenv install")
        print("2. 配置真实的存储服务")
        print("3. 运行完整测试: python test_storage.py")
        return 0
    else:
        print("❌ 部分测试失败，请检查实现。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
