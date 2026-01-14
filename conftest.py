# conftest.py
"""
全局测试配置文件：自动清理测试创建的 Assets 目录

这个配置文件包含两个清理 fixture：
1. cleanup_test_assets_per_function - 每个测试函数后清理（适用于 pytest 风格测试）
2. cleanup_test_assets_session - 整个测试会话结束后清理（适用于 Django TestCase）

确保测试环境的纯净性，无论使用哪种测试风格。
"""
import pytest
import shutil
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# 定义需要保留的目录（不应被清理的目录）
PRESERVED_DIRS = {'admin'}


def _cleanup_test_assets(before_assets_dirs=None):
    """
    清理测试创建的 Assets 目录的通用函数
    
    Args:
        before_assets_dirs: 测试前已存在的目录集合。如果为 None，则清理所有非保留目录。
    """
    try:
        assets_base = Path(settings.ASSETS_BASE_PATH)
        if not assets_base.exists():
            return  # Assets 目录不存在，无需清理
        
        # 获取当前的 Assets 目录列表
        current_assets_dirs = {d.name for d in assets_base.iterdir() if d.is_dir()}
        
        # 确定需要清理的目录
        if before_assets_dirs is not None:
            # 清理新创建的目录（测试前不存在，测试后存在的目录）
            dirs_to_clean = current_assets_dirs - before_assets_dirs
        else:
            # 清理所有非保留目录
            dirs_to_clean = current_assets_dirs - PRESERVED_DIRS
        
        if dirs_to_clean:
            logger.info(f"检测到需要清理的 Assets 目录: {dirs_to_clean}")
        
        for dir_name in dirs_to_clean:
            user_assets_path = assets_base / dir_name
            if user_assets_path.exists() and user_assets_path.is_dir():
                try:
                    shutil.rmtree(user_assets_path)
                    logger.info(f"已清理测试 Assets 目录: {user_assets_path}")
                except Exception as e:
                    logger.warning(f"清理测试 Assets 目录失败 {user_assets_path}: {str(e)}")
    except Exception as e:
        logger.warning(f"清理测试 Assets 目录时出错: {str(e)}")


@pytest.fixture(autouse=True, scope='function')
def cleanup_test_assets_per_function():
    """
    每个测试函数后自动清理 Assets 目录
    
    这个 fixture 会在每个测试函数执行前后自动运行：
    1. 测试前：记录已存在的 Assets 目录
    2. 测试后：清理新创建的 Assets 目录
    
    适用于 pytest 风格的测试（使用 @pytest.mark.django_db 的测试）。
    
    注意：由于 pytest-django 使用数据库事务回滚，测试创建的用户会被自动删除，
    但文件系统中的目录不会自动删除。此 fixture 通过对比文件系统状态来清理目录。
    """
    # 记录测试前的 Assets 目录
    try:
        assets_base = Path(settings.ASSETS_BASE_PATH)
        before_assets_dirs = set()
        if assets_base.exists():
            before_assets_dirs = {d.name for d in assets_base.iterdir() if d.is_dir()}
            logger.debug(f"测试前 Assets 目录: {before_assets_dirs}")
    except Exception as e:
        logger.warning(f"获取测试前 Assets 目录状态失败: {str(e)}")
        before_assets_dirs = set()
    
    yield
    
    # 测试后清理新创建的 Assets 目录
    _cleanup_test_assets(before_assets_dirs)


@pytest.fixture(autouse=True, scope='session')
def cleanup_test_assets_session():
    """
    整个测试会话结束后清理所有测试创建的 Assets 目录
    
    这个 fixture 在所有测试运行完成后执行，清理所有非保留的用户目录。
    
    适用于 Django TestCase 风格的测试，因为这些测试不会触发 function 级别的 fixture。
    
    保留目录：
    - admin: 系统管理员目录，包含示例文件
    
    清理目录：
    - testuser, user1, user2, 张三 等测试用户目录
    """
    yield
    
    # 所有测试完成后，清理所有非保留目录
    logger.info("测试会话结束，开始清理所有测试 Assets 目录...")
    _cleanup_test_assets()

