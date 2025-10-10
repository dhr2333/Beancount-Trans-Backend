# bin/ 目录说明

本目录包含项目的运维脚本和工具。

## 📁 脚本清单

### 🚀 部署相关

#### `docker_start.sh`
Docker 容器启动脚本

**用途**: 
- 容器启动时的入口脚本
- 设置环境变量
- 执行静态文件收集
- 启动 uWSGI 服务器

**使用**:
```bash
# 在 Dockerfile 中作为 ENTRYPOINT
ENTRYPOINT ["/code/beancount-trans/bin/docker_start.sh"]
```

**关键配置**:
- 工作目录: `/code/beancount-trans`
- Django 设置: `project.settings.develop`
- 服务器: uWSGI (通过 `conf/uwsgi.ini`)

---

### 🔄 异步任务相关

#### `celery_worker_start.sh`
Celery Worker 启动脚本

**用途**: 
- 启动 Celery 异步任务处理器
- 处理账单解析等后台任务

**使用**:
```bash
# 在容器中运行
docker exec <container_id> /bin/bash /code/beancount-trans/bin/celery_worker_start.sh

# 本地开发环境
pipenv run bash bin/celery_worker_start.sh
```

**关键配置**:
- 队列: default
- 并发: 根据 CPU 核心数自动设置
- 日志: `logs/celery_worker.log`

#### `celery_beat_start.sh`
Celery Beat 定时任务调度器启动脚本

**用途**: 
- 启动定时任务调度器
- 管理周期性任务（如定时清理、数据统计等）

**使用**:
```bash
# 在容器中运行
docker exec <container_id> /bin/bash /code/beancount-trans/bin/celery_beat_start.sh

# 本地开发环境
pipenv run bash bin/celery_beat_start.sh
```

**关键配置**:
- 调度器: DatabaseScheduler
- 日志: `logs/celery_beat.log`

---

### 🔍 运维工具

#### `check_system_status.py` ✨
系统状态检查脚本

**用途**: 
- 快速检查系统核心组件状态
- 验证官方模板是否正确初始化
- 查看数据库统计信息

**使用**:
```bash
# 本地开发环境（从项目根目录）
pipenv run python bin/check_system_status.py

# 本地开发环境（从 bin 目录）
cd bin && pipenv run python check_system_status.py

# Docker 容器中
docker exec <container_id> python bin/check_system_status.py

# 或者直接执行（需要有执行权限）
docker exec <container_id> /code/beancount-trans/bin/check_system_status.py
```

**输出示例**:
```
============================================================
Beancount-Trans 系统状态
============================================================

✓ 默认用户: admin

【官方模板】
  账户模板: 1 个
  映射模板: 3 个

【admin 用户数据】
  账户: 85
  支出映射: 30
  资产映射: 7
  收入映射: 2
  格式化配置: BERT

【所有用户统计】
  总用户数: 29
  活跃用户: 29

【数据库统计】
  总账户数: 204
  总映射数: 618

============================================================
系统状态正常
============================================================
```

**检查项**:
- ✓ 默认用户（id=1, 通常是 admin）是否存在
- ✓ 官方模板数量（账户模板、映射模板）
- ✓ admin 用户的数据完整性
- ✓ 系统用户统计
- ✓ 数据库数据量统计

---

#### `backup.sh`
数据备份脚本

**用途**: 
- 备份数据库数据
- 备份用户上传的文件

**使用**:
```bash
# 执行备份
bash bin/backup.sh
```

---

#### `wait-for-it.sh`
等待服务就绪脚本

**用途**: 
- 等待依赖服务（如数据库、Redis）启动完成
- Docker Compose 服务编排中的依赖管理

**使用**:
```bash
# 等待 MySQL 就绪
./bin/wait-for-it.sh mysql:3306 -t 60

# 等待 Redis 就绪
./bin/wait-for-it.sh redis:6379 -t 30
```

**参数**:
- `host:port` - 要等待的服务地址和端口
- `-t timeout` - 超时时间（秒）

---

## 🐳 Docker 容器中的使用

### 容器内路径
- 项目根目录: `/code/beancount-trans/`
- 脚本目录: `/code/beancount-trans/bin/`
- Python 环境: `/root/.local/bin/python`

### 执行权限
所有 `.sh` 和 `.py` 脚本在构建时自动添加执行权限（参见 `Dockerfile-Backend`）

### 常用操作

#### 进入容器
```bash
docker exec -it <container_id> /bin/bash
```

#### 检查系统状态
```bash
docker exec <container_id> python bin/check_system_status.py
```

#### 启动 Celery Worker
```bash
docker exec -d <container_id> /bin/bash /code/beancount-trans/bin/celery_worker_start.sh
```

#### 启动 Celery Beat
```bash
docker exec -d <container_id> /bin/bash /code/beancount-trans/bin/celery_beat_start.sh
```

---

## 📝 开发说明

### 添加新脚本

1. **创建脚本文件**
   ```bash
   touch bin/my_script.sh
   chmod +x bin/my_script.sh
   ```

2. **添加 Shebang**
   ```bash
   #!/bin/bash
   # 或
   #!/usr/bin/env python
   ```

3. **更新 Dockerfile**
   在 `Dockerfile-Backend` 中添加执行权限：
   ```dockerfile
   RUN chmod +x /code/beancount-trans/bin/my_script.sh
   ```

4. **更新本文档**
   在本 README 中添加脚本说明

### Python 脚本编写规范

所有 Python 运维脚本应该包含以下结构：

```python
#!/usr/bin/env python
"""
脚本功能说明

使用方法：
  python bin/script_name.py [参数]
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

# Django 初始化
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.develop')
django.setup()

# 导入项目模块
from project.apps.xxx import xxx

def main():
    """主函数"""
    pass

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"✗ 错误: {str(e)}")
        sys.exit(1)
```

**关键点**:
1. ✅ 使用 `Path(__file__).resolve().parent.parent` 获取项目根目录
2. ✅ 将项目根添加到 `sys.path`
3. ✅ 切换工作目录到项目根（`os.chdir`）
4. ✅ 使用 `project.settings.develop` 作为 Django 设置
5. ✅ 完整的异常处理和退出码

---

## 🔧 故障排查

### 问题：脚本报 "ModuleNotFoundError"

**原因**: Python 无法找到 `project` 模块

**解决**:
1. 确认在项目根目录或 bin 目录运行
2. 使用 `pipenv run python` 而不是直接 `python`
3. 检查脚本是否正确设置了 `sys.path`

### 问题：脚本没有执行权限

**解决**:
```bash
chmod +x bin/script_name.sh
```

### 问题：容器中脚本找不到

**解决**:
1. 检查 `Dockerfile-Backend` 是否包含 `COPY bin ./bin`
2. 重新构建镜像: `docker-compose build backend`

---

## 📚 相关文档

- [Docker 部署指南](../docs/DEPLOYMENT_CHECKLIST.md)
- [Celery 配置说明](../project/celery.py)
- [系统架构文档](../docs/TEMPLATE_SYSTEM.md)

---

**最后更新**: 2025-10-10  
**维护者**: Beancount-Trans 开发团队

