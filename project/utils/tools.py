# project/utils/tools.py
from datetime import datetime
from django.contrib.auth import get_user_model
from project.apps.translate.models import FormatConfig


def time_to_timestamp(time_str):
    # 将时间字符串转换为datetime对象
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    # 转换datetime为时间戳
    timestamp = int(dt.timestamp())
    return timestamp


def timestamp_to_time(timestamp):
    # 从时间戳转换回datetime对象
    dt = datetime.fromtimestamp(timestamp)
    # 格式化datetime为字符串
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    return time_str


User = get_user_model()

def get_user_config(user=None):
    """
    获取用户配置（带默认值回退）
    用法：config = get_user_config(request.user)
    """
    if user and not user.is_anonymous:
        return FormatConfig.get_user_config(user)
    # 返回默认配置（用于未登录状态）
    return FormatConfig(
        flag = "*",
        show_note = True,
        show_tag = True,
        show_time = True,
        show_uuid = True,
        show_status = True,
        show_discount = True,
        income_template = None,
        commission_template = None,
        currency = 'CNY'
    )
