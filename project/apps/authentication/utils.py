import re
from typing import Tuple
from django.contrib.auth.models import User


def is_valid_username_format(username: str, allow_phone_format: bool = False) -> bool:
    """验证用户名格式是否有效
    
    禁止以下格式：
    1. Git 仓库目录名格式：`^[a-f0-9]{6,}-assets$`（保留给 Git 仓库目录名使用）
    2. 手机号注册格式：`^\\d+$`（保留给手机号注册时自动生成的用户名，避免占用）
    
    Args:
        username: 待验证的用户名
        allow_phone_format: 是否允许手机号格式（内部使用，如自动生成时）
        
    Returns:
        bool: 如果格式有效返回 True，否则返回 False
    """
    if not username:
        return False
    
    # 禁止 Git 仓库目录名格式（如 abc123-assets）
    git_repo_pattern = re.compile(r'^[a-f0-9]{6,}-assets$', re.IGNORECASE)
    if git_repo_pattern.match(username):
        return False
    
    # 禁止手机号注册格式（如 user_13800138000），除非是内部生成
    if not allow_phone_format:
        phone_format_pattern = re.compile(r'^\d{11}$', re.IGNORECASE)
        if phone_format_pattern.match(username):
            return False
    
    return True


def generate_unique_username(base_username: str) -> str:
    """根据候选值生成唯一用户名，冲突时自动添加数字后缀
    
    如果提供的用户名与 Git 仓库目录名格式冲突，会自动添加后缀以避免冲突。
    
    Args:
        base_username: 基础用户名
        
    Returns:
        str: 唯一的用户名
    """
    base = (base_username or '').strip()
    
    # 如果用户名太短或为空，生成默认用户名
    if len(base) < 3:
        base = f"user_{base}" if base else 'user'
    
    # 截断到最大长度（Django User.username 字段最大长度为 150）
    base = base[:150]
    
    # 如果基础用户名格式无效（如匹配 Git 仓库名格式），强制添加后缀
    # 注意：这里允许手机号格式，因为是自动生成场景
    if not is_valid_username_format(base, allow_phone_format=True):
        base = f"{base}_user"
    
    # 尝试使用基础用户名
    candidate = base
    suffix = 1
    
    # 循环直到找到唯一的用户名
    # 注意：自动生成时允许手机号格式
    while User.objects.filter(username=candidate).exists() or not is_valid_username_format(candidate, allow_phone_format=True):
        # 生成后缀，确保总长度不超过 150
        tail = f"_{suffix}"
        allowed = 150 - len(tail)
        candidate = f"{base[:allowed]}{tail}"
        suffix += 1
        
        # 防止无限循环（理论上不会发生，但安全起见）
        if suffix > 10000:
            # 使用随机后缀作为最后的备选方案
            import random
            tail = f"_{random.randint(1000, 9999)}"
            allowed = 150 - len(tail)
            candidate = f"{base[:allowed]}{tail}"
            break
    
    return candidate


def validate_username_format(username: str, allow_phone_format: bool = False) -> Tuple[bool, str]:
    """验证用户名格式并返回结果
    
    Args:
        username: 待验证的用户名
        allow_phone_format: 是否允许手机号格式（内部使用，如自动生成时）
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid: 是否有效
            - error_message: 错误信息（如果无效）
    """
    if not username or not username.strip():
        return False, "用户名不能为空"
    
    username = username.strip()
    
    # 检查 Git 仓库目录名格式
    git_repo_pattern = re.compile(r'^[a-f0-9]{6,}-assets$', re.IGNORECASE)
    if git_repo_pattern.match(username):
        return False, "用户名不能使用 Git 仓库目录名格式（如：abc123-assets）"
    
    # 检查手机号注册格式
    if not allow_phone_format:
        phone_format_pattern = re.compile(r'^\d{11}$', re.IGNORECASE)
        if phone_format_pattern.match(username):
            return False, "用户名不能使用手机号注册格式（如：13800138000），此格式为系统自动生成专用"
    
    if not is_valid_username_format(username, allow_phone_format=allow_phone_format):
        # 这个分支理论上不会到达，因为上面已经检查了，但保留作为兜底
        return False, "用户名格式无效"
    
    return True, ""

