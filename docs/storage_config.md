# 存储配置文档

本项目支持多种存储后端，包括MinIO、阿里云OSS和通用S3兼容存储。通过统一的抽象层，可以轻松切换不同的存储服务。

## 支持的存储类型

### 1. MinIO (本地/私有云)
- 适用于开发环境和私有部署
- 兼容S3协议
- 免费开源

### 2. 阿里云OSS (生产环境推荐)
- 高可用、高可靠
- 支持多种存储类型
- 丰富的安全特性

### 3. 通用S3兼容存储
- 支持AWS S3、腾讯云COS等
- 使用boto3库
- 完全兼容S3协议

## 配置说明

### 存储类型选择

在配置文件中设置 `STORAGE_TYPE`：

```python
# 使用MinIO
STORAGE_TYPE = 'minio'

# 使用阿里云OSS
STORAGE_TYPE = 'oss'

# 使用通用S3
STORAGE_TYPE = 's3'
```

### MinIO配置

```python
MINIO_CONFIG = {
    'ENDPOINT': '127.0.0.1:9000',  # MinIO服务器地址
    'ACCESS_KEY': 'minioadmin',     # 访问密钥
    'SECRET_KEY': 'minioadmin',     # 密钥
    'BUCKET_NAME': 'beancount-trans', # 存储桶名称
    'USE_HTTPS': False              # 是否使用HTTPS
}
```

### 阿里云OSS配置

```python
OSS_CONFIG = {
    'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',  # OSS端点
    'ACCESS_KEY_ID': 'your_access_key_id',               # AccessKey ID
    'ACCESS_KEY_SECRET': 'your_access_key_secret',       # AccessKey Secret
    'BUCKET_NAME': 'beancount-trans',                    # 存储桶名称
    'REGION': 'cn-hangzhou'                              # 地域
}
```

### S3配置

```python
S3_CONFIG = {
    'ENDPOINT_URL': 'https://s3.amazonaws.com',          # S3端点
    'ACCESS_KEY_ID': 'your_access_key_id',               # 访问密钥ID
    'SECRET_ACCESS_KEY': 'your_secret_access_key',       # 密钥
    'BUCKET_NAME': 'beancount-trans',                    # 存储桶名称
    'REGION': 'us-east-1',                               # 地域
    'USE_SSL': True,                                     # 使用SSL
    'VERIFY_SSL': True                                   # 验证SSL证书
}
```

## 环境配置

### 开发环境 (develop.py)
```python
STORAGE_TYPE = 'oss'  # 使用阿里云OSS
```

### 生产环境 (prod.py)
```python
STORAGE_TYPE = 'oss'  # 使用阿里云OSS
```

### Docker本地环境 (docker_local.py)
```python
STORAGE_TYPE = 'minio'  # 使用MinIO
```

## 使用示例

### 在代码中使用

```python
from project.utils.storage_factory import get_storage_client

# 获取存储客户端
storage_client = get_storage_client()

# 上传文件
with open('file.txt', 'rb') as f:
    success = storage_client.upload_file('path/to/file.txt', f, 'text/plain')

# 下载文件
file_data = storage_client.download_file('path/to/file.txt')
if file_data:
    content = file_data.read()

# 删除文件
success = storage_client.delete_file('path/to/file.txt')

# 检查文件是否存在
exists = storage_client.file_exists('path/to/file.txt')

# 获取文件访问URL
url = storage_client.get_file_url('path/to/file.txt', expires=3600)
```

### 在视图中使用

```python
from project.utils.storage_factory import get_storage_client

class FileViewSet(ModelViewSet):
    def create(self, request):
        storage_client = get_storage_client()
        uploaded_file = request.FILES['file']
        
        # 上传文件
        success = storage_client.upload_file(
            storage_name,
            uploaded_file,
            content_type=uploaded_file.content_type
        )
        
        if success:
            # 保存到数据库
            file_obj = File.objects.create(...)
            return Response(...)
        else:
            return Response({"error": "上传失败"}, status=400)
```

## 迁移指南

### 从MinIO迁移到OSS

1. 更新配置文件：
   ```python
   STORAGE_TYPE = 'oss'
   ```

2. 配置OSS参数：
   ```python
   OSS_CONFIG = {
       'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
       'ACCESS_KEY_ID': 'your_access_key_id',
       'ACCESS_KEY_SECRET': 'your_access_key_secret',
       'BUCKET_NAME': 'your_bucket_name',
       'REGION': 'cn-hangzhou'
   }
   ```

3. 安装依赖：
   ```bash
   pip install oss2
   ```

4. 重启应用

### 数据迁移

如果需要将现有数据从MinIO迁移到OSS：

1. 使用MinIO客户端下载所有文件
2. 使用OSS客户端上传文件
3. 更新数据库中的文件路径（如果需要）

## 注意事项

1. **安全性**：生产环境请使用环境变量存储敏感信息
2. **性能**：OSS内网Endpoint可以提供更好的性能
3. **成本**：不同存储服务的计费方式不同，请根据实际需求选择
4. **兼容性**：所有存储后端都实现了相同的接口，可以无缝切换

## 故障排除

### 常见错误

1. **连接失败**：检查网络连接和配置参数
2. **权限错误**：检查AccessKey和SecretKey是否正确
3. **Bucket不存在**：确保Bucket已创建且有访问权限

### 日志查看

存储操作的日志会记录在 `logs/beancount-trans.log` 中，可以通过查看日志来诊断问题。
