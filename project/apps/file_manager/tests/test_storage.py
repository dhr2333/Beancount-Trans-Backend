#!/usr/bin/env python3
"""
存储功能测试脚本
用于测试不同存储后端的连接和基本功能
"""

import os
import sys
import django
from io import BytesIO

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.develop')
django.setup()

from project.utils.storage_factory import get_storage_client


def test_storage_backend():
    """测试存储后端功能"""
    print("开始测试存储后端...")
    
    try:
        # 获取存储客户端
        storage_client = get_storage_client()
        print(f"✓ 成功获取存储客户端: {type(storage_client).__name__}")
        
        # 测试文件
        test_file_name = "test_storage.txt"
        test_content = b"This is a test file for storage verification.\nHello, Storage!"
        
        # 创建测试文件流
        file_stream = BytesIO(test_content)
        
        # 测试上传
        print("测试文件上传...")
        success = storage_client.upload_file(
            test_file_name,
            file_stream,
            content_type='text/plain'
        )
        
        if success:
            print("✓ 文件上传成功")
        else:
            print("✗ 文件上传失败")
            return False
        
        # 测试文件存在性
        print("测试文件存在性检查...")
        exists = storage_client.file_exists(test_file_name)
        if exists:
            print("✓ 文件存在性检查通过")
        else:
            print("✗ 文件存在性检查失败")
            return False
        
        # 测试下载
        print("测试文件下载...")
        downloaded_data = storage_client.download_file(test_file_name)
        if downloaded_data:
            content = downloaded_data.read()
            if content == test_content:
                print("✓ 文件下载成功，内容正确")
            else:
                print("✗ 文件下载成功，但内容不正确")
                return False
        else:
            print("✗ 文件下载失败")
            return False
        
        # 测试获取URL
        print("测试获取文件URL...")
        url = storage_client.get_file_url(test_file_name, expires=3600)
        if url:
            print(f"✓ 成功获取文件URL: {url[:50]}...")
        else:
            print("✗ 获取文件URL失败")
        
        # 测试删除
        print("测试文件删除...")
        delete_success = storage_client.delete_file(test_file_name)
        if delete_success:
            print("✓ 文件删除成功")
        else:
            print("✗ 文件删除失败")
            return False
        
        # 验证删除
        exists_after_delete = storage_client.file_exists(test_file_name)
        if not exists_after_delete:
            print("✓ 文件删除验证通过")
        else:
            print("✗ 文件删除验证失败")
            return False
        
        print("\n🎉 所有测试通过！存储后端工作正常。")
        return True
        
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """测试配置信息"""
    print("检查存储配置...")
    
    from django.conf import settings
    
    storage_type = getattr(settings, 'STORAGE_TYPE', 'minio')
    print(f"存储类型: {storage_type}")
    
    if storage_type == 'minio':
        config = getattr(settings, 'MINIO_CONFIG', {})
        print(f"MinIO配置: {config}")
    elif storage_type == 'oss':
        config = getattr(settings, 'OSS_CONFIG', {})
        print(f"OSS配置: {config}")
    elif storage_type == 's3':
        config = getattr(settings, 'S3_CONFIG', {})
        print(f"S3配置: {config}")
    
    print("✓ 配置检查完成\n")


if __name__ == "__main__":
    print("=" * 50)
    print("存储功能测试")
    print("=" * 50)
    
    # 测试配置
    test_configuration()
    
    # 测试存储功能
    success = test_storage_backend()
    
    print("=" * 50)
    if success:
        print("✅ 测试完成，所有功能正常")
        sys.exit(0)
    else:
        print("❌ 测试失败，请检查配置和网络连接")
        sys.exit(1)
