# 🚀 Beancount-Trans 快速参考

## 常用命令

### 本地开发

```bash
# 启动开发服务器
pipenv run python manage.py runserver

# 数据库迁移
pipenv run python manage.py makemigrations
pipenv run python manage.py migrate

# 创建超级用户
pipenv run python manage.py createsuperuser

# 初始化官方模板
pipenv run python manage.py init_official_templates

# 检查系统状态
pipenv run python bin/check_system_status.py

# 启动 Celery Worker
pipenv run celery -A project worker -l info

# 启动 Celery Beat
pipenv run celery -A project beat -l info
```

### Docker 容器

```bash
# 构建镜像
docker-compose build backend

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 进入容器
docker exec -it <container_id> /bin/bash

# 执行管理命令
docker exec <container_id> python manage.py <command>

# 检查系统状态
docker exec <container_id> python bin/check_system_status.py

# 数据库迁移
docker exec <container_id> python manage.py migrate

# 初始化官方模板（首次部署）
docker exec <container_id> python manage.py init_official_templates

# 重启服务
docker-compose restart backend
```

## 项目结构

```
Beancount-Trans-Backend/
├── bin/                          # 运维脚本
│   ├── check_system_status.py   # 系统状态检查
│   ├── docker_start.sh           # Docker 启动脚本
│   ├── celery_worker_start.sh   # Celery Worker 启动
│   ├── celery_beat_start.sh     # Celery Beat 启动
│   └── README.md                 # 脚本使用说明
├── project/
│   ├── apps/
│   │   ├── account/              # 账户管理
│   │   ├── maps/                 # 映射管理
│   │   ├── translate/            # 账单解析
│   │   ├── file_manager/         # 文件管理
│   │   ├── fava_instances/       # Fava 实例
│   │   └── tags/                 # 标签管理
│   ├── settings/
│   │   ├── develop.py            # 开发环境配置
│   │   └── production.py         # 生产环境配置
│   └── celery.py                 # Celery 配置
├── docs/                         # 文档
├── conf/                         # 配置文件
├── logs/                         # 日志文件
└── manage.py                     # Django 管理脚本
```

## 重要端点

### API 端点

- `/api/account/` - 账户管理
- `/api/account-templates/` - 账户模板
- `/api/templates/` - 映射模板
- `/api/translate/trans` - 单文件解析
- `/api/translate/multi` - 多文件解析

### 管理后台

- `/admin/` - Django Admin
- `/api/schema/swagger-ui/` - API 文档

## 故障排查

### 问题：容器启动失败

```bash
# 查看日志
docker-compose logs backend

# 检查配置
docker exec <container_id> env | grep DJANGO

# 测试数据库连接
docker exec <container_id> python manage.py dbshell
```

### 问题：账单解析失败

```bash
# 检查系统状态
docker exec <container_id> python bin/check_system_status.py

# 查看 Celery 日志
docker-compose logs celery_worker

# 检查官方模板
docker exec <container_id> python manage.py shell
>>> from project.apps.account.models import AccountTemplate
>>> AccountTemplate.objects.filter(is_official=True).count()
```

### 问题：模板未初始化

```bash
# 初始化官方模板
docker exec <container_id> python manage.py init_official_templates

# 验证
docker exec <container_id> python bin/check_system_status.py
```

## 环境变量

关键环境变量（在 docker-compose.yml 或 .env 中配置）：

```bash
# Django
DJANGO_SETTINGS_MODULE=project.settings.production
SECRET_KEY=<your-secret-key>
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# 数据库
DB_ENGINE=django.db.backends.mysql
DB_NAME=beancount
DB_USER=root
DB_PASSWORD=<password>
DB_HOST=mysql
DB_PORT=3306

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

## 更多文档

- [bin/ 脚本说明](bin/README.md)
- [模板系统架构](docs/TEMPLATE_SYSTEM.md)
- [部署检查清单](docs/DEPLOYMENT_CHECKLIST.md)
- [API 文档](docs/API_DOCUMENTATION.md)

---

**最后更新**: 2025-10-10
