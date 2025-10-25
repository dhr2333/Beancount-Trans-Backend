# 环境变量配置文档

本文档详细说明了 Beancount-Trans 项目的所有环境变量配置、部署方式和启动命令。

## 概述

项目采用统一配置架构，通过环境变量管理不同环境的配置：
- **本地开发**: 使用 `.env` 文件
- **开源用户**: 使用 `docker-compose.example.yaml` 示例配置

## 环境变量说明

### Django 核心配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `DJANGO_SECRET_KEY` | ✅ | 无 | Django 密钥，生产环境必须修改为随机字符串 |
| `DJANGO_DEBUG` | ❌ | `False` | 调试模式，生产环境必须设置为 False |
| `DJANGO_ALLOWED_HOSTS` | ❌ | `localhost,127.0.0.1` | 允许的主机名（逗号分隔） |
| `CSRF_TRUSTED_ORIGINS` | ❌ | `http://localhost` | CSRF 信任的来源（逗号分隔） |

### 数据库配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `TRANS_POSTGRESQL_DATABASE` | ❌ | `beancount-trans` | PostgreSQL 数据库名 |
| `TRANS_POSTGRESQL_USER` | ❌ | `postgres` | PostgreSQL 用户名 |
| `TRANS_POSTGRESQL_PASSWORD` | ✅ | 无 | PostgreSQL 密码 |
| `TRANS_POSTGRESQL_HOST` | ❌ | `127.0.0.1` | PostgreSQL 主机 |
| `TRANS_POSTGRESQL_PORT` | ❌ | `5432` | PostgreSQL 端口 |

### Redis 配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `TRANS_REDIS_HOST` | ❌ | `127.0.0.1` | Redis 主机 |
| `TRANS_REDIS_PORT` | ❌ | `6379` | Redis 端口 |
| `TRANS_REDIS_PASSWORD` | ✅ | 无 | Redis 密码 |

### 存储配置

#### 存储类型
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `STORAGE_TYPE` | ❌ | `minio` | 存储类型：`minio` / `oss` / `s3` |

#### MinIO 配置（默认）
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `MINIO_ENDPOINT` | ❌ | `127.0.0.1:9000` | MinIO 端点 |
| `MINIO_ACCESS_KEY` | ❌ | `minioadmin` | MinIO 访问密钥 |
| `MINIO_SECRET_KEY` | ❌ | `minioadmin` | MinIO 密钥 |
| `MINIO_BUCKET_NAME` | ❌ | `beancount-trans` | 存储桶名称 |
| `MINIO_USE_HTTPS` | ❌ | `False` | 是否使用 HTTPS |

#### 阿里云 OSS 配置（可选）
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `OSS_ENDPOINT` | ❌ | `oss-cn-hangzhou.aliyuncs.com` | OSS 端点 |
| `OSS_ACCESS_KEY_ID` | ❌ | 无 | OSS 访问密钥 ID |
| `OSS_ACCESS_KEY_SECRET` | ❌ | 无 | OSS 访问密钥 Secret |
| `OSS_BUCKET_NAME` | ❌ | `beancount-trans` | OSS 存储桶名称 |
| `OSS_REGION` | ❌ | `cn-hangzhou` | OSS 区域 |

#### AWS S3 配置（可选）
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `S3_ENDPOINT_URL` | ❌ | `https://s3.amazonaws.com` | S3 端点 URL |
| `S3_ACCESS_KEY_ID` | ❌ | 无 | S3 访问密钥 ID |
| `S3_SECRET_ACCESS_KEY` | ❌ | 无 | S3 访问密钥 |
| `S3_BUCKET_NAME` | ❌ | `beancount-trans` | S3 存储桶名称 |
| `S3_REGION` | ❌ | `us-east-1` | S3 区域 |
| `S3_USE_SSL` | ❌ | `True` | 是否使用 SSL |
| `S3_VERIFY_SSL` | ❌ | `True` | 是否验证 SSL |

### CORS 跨域配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `CORS_ALLOWED_ORIGINS` | ❌ | `http://localhost:5173,http://127.0.0.1:5173` | 允许的跨域来源（逗号分隔） |

### JWT 令牌配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `JWT_ACCESS_TOKEN_HOURS` | ❌ | `1` (生产) / `72` (开发) | JWT 访问令牌有效期（小时） |

### Traefik/Fava 容器配置

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `TRAEFIK_NETWORK` | ❌ | `shared-network` | Traefik 网络名称 |
| `FAVA_IMAGE` | ❌ | `harbor.dhr2333.cn/beancount-trans-assets:develop` | Fava 容器镜像 |
| `BASE_URL` | ❌ | `localhost` | 基础 URL |
| `CERTRESOLVER` | ❌ | `alicloud-dns` | 证书解析器 |

### Assets 文件路径

| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `ASSETS_HOST_PATH` | ❌ | 项目根目录/Assets | 宿主机上 Assets 目录的绝对路径 |

### OAuth 第三方登录配置（可选）

#### GitHub OAuth
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `GITHUB_CLIENT_ID` | ❌ | 无 | GitHub OAuth 客户端 ID |
| `GITHUB_CLIENT_SECRET` | ❌ | 无 | GitHub OAuth 客户端密钥 |

#### Google OAuth
| 变量名 | 必需 | 默认值 | 说明 |
|---------|------|--------|------|
| `GOOGLE_CLIENT_ID` | ❌ | 无 | Google OAuth 客户端 ID |
| `GOOGLE_CLIENT_SECRET` | ❌ | 无 | Google OAuth 客户端密钥 |

## 部署方式

### 1. 本地开发环境

#### 使用 .env 文件（推荐）

1. **复制环境变量模板**
   ```bash
   cp .env.example .env
   ```

2. **修改 .env 文件**
   编辑 `.env` 文件，配置您的本地开发环境参数：
   ```bash
   # 开发环境配置
   DJANGO_DEBUG=True
   DJANGO_SECRET_KEY=your-development-secret-key
   
   # 数据库配置
   TRANS_POSTGRESQL_HOST=127.0.0.1
   TRANS_POSTGRESQL_PORT=5432
   TRANS_POSTGRESQL_USER=your-username
   TRANS_POSTGRESQL_PASSWORD=your-password
   
   # Redis 配置
   TRANS_REDIS_HOST=127.0.0.1
   TRANS_REDIS_PORT=6379
   TRANS_REDIS_PASSWORD=your-redis-password
   
   # 其他配置...
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行数据库迁移**
   ```bash
   python manage.py migrate
   ```

5. **启动开发服务器**
   ```bash
   python manage.py runserver 0:8002
   ```

#### 使用系统环境变量

如果不使用 `.env` 文件，可以通过系统环境变量配置：

```bash
export DJANGO_SECRET_KEY="your-secret-key"
export DJANGO_DEBUG=True
export TRANS_POSTGRESQL_PASSWORD="your-password"
# ... 其他环境变量

python manage.py runserver 0:8002
```

#### 使用现有的生产配置

如果您已有生产环境的 docker-compose 配置，只需修改 `DJANGO_SETTINGS_MODULE`：

```yaml
environment:
  - DJANGO_SETTINGS_MODULE=project.settings.settings  # 改为统一配置
  # ... 其他环境变量
```

### 2. 开源用户部署

#### 快速开始

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/Beancount-Trans-Backend.git
   cd Beancount-Trans-Backend
   ```

2. **复制配置**
   ```bash
   cp docker-compose.example.yaml docker-compose.yaml
   cp .env.example .env
   ```

3. **修改配置**
   - 编辑 `docker-compose.yaml` 中的密码和域名
   - 编辑 `.env` 文件中的配置（如果使用本地开发）

4. **启动服务**
   ```bash
   # 使用 Docker Compose（推荐）
   docker-compose up -d
   
   # 或本地开发
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver 0:8000
   ```

## 环境变量优先级

环境变量的加载优先级（从高到低）：
1. 系统环境变量
2. docker-compose 环境变量
3. `.env` 文件
4. 默认值

## 常见问题

### Q: 如何生成 Django SECRET_KEY？
A: 可以使用以下命令生成：
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Q: 开发环境和生产环境的 JWT 有效期如何设置？
A: 
- 开发环境：`JWT_ACCESS_TOKEN_HOURS=72`（3天）
- 生产环境：`JWT_ACCESS_TOKEN_HOURS=1`（1小时）

### Q: 如何配置 OAuth 登录？
A: 
1. 在 GitHub/Google 开发者控制台创建 OAuth 应用
2. 获取 Client ID 和 Client Secret
3. 在环境变量中配置 `GITHUB_CLIENT_ID`、`GITHUB_CLIENT_SECRET` 等

### Q: 如何切换存储类型？
A: 修改 `STORAGE_TYPE` 环境变量：
- `STORAGE_TYPE=minio` - 使用 MinIO（默认）
- `STORAGE_TYPE=oss` - 使用阿里云 OSS
- `STORAGE_TYPE=s3` - 使用 AWS S3
