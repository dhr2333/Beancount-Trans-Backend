"""
测试环境专用Django配置
- 使用SQLite内存数据库
- 使用内存缓存
- 禁用Celery任务
- 简化日志输出
"""
from .develop import *

# 测试模式标记
TESTING = True

# 使用SQLite内存数据库进行测试
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 使用内存缓存，无需Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-session-cache',
    },
}

# 禁用Celery任务执行（同步执行）
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 简化密码验证以加快测试速度
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 禁用密码验证器
AUTH_PASSWORD_VALIDATORS = []

# 简化日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# 禁用调试工具栏
DEBUG_TOOLBAR = False

# 静态文件收集（测试时不需要）
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# 邮件后端使用内存
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 测试时禁用某些中间件以加速
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug' not in m.lower()]

# 存储配置 - 使用本地文件系统
STORAGE_TYPE = 'local'

# 测试报告输出目录
TEST_REPORTS_DIR = BASE_DIR / 'reports'
