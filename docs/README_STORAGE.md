# 存储系统使用说明

本项目现在支持多种存储后端，包括MinIO、阿里云OSS和通用S3兼容存储。通过统一的抽象层，可以轻松切换不同的存储服务。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置存储类型

在相应的配置文件中设置 `STORAGE_TYPE`：

- **开发环境** (`project/settings/develop.py`): 使用OSS
- **生产环境** (`project/settings/prod.py`): 使用OSS  
- **Docker本地** (`project/settings/docker_local.py`): 使用MinIO

### 3. 配置存储参数

根据选择的存储类型，配置相应的参数：

#### MinIO配置
```python
MINIO_CONFIG = {
    'ENDPOINT': '127.0.0.1:9000',
    'ACCESS_KEY': 'minioadmin',
    'SECRET_KEY': 'minioadmin',
    'BUCKET_NAME': 'beancount-trans',
    'USE_HTTPS': False
}
```

#### 阿里云OSS配置
```python
OSS_CONFIG = {
    'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
    'ACCESS_KEY_ID': 'your_access_key_id',
    'ACCESS_KEY_SECRET': 'your_access_key_secret',
    'BUCKET_NAME': 'beancount-trans',
    'REGION': 'cn-hangzhou'
}
```

### 4. 测试存储功能

运行测试脚本验证配置：

```bash
python test_storage.py
```

## 代码使用示例

### 基本使用

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

### 在Django视图中使用

```python
from project.utils.storage_factory import get_storage_client

class FileViewSet(ModelViewSet):
    def create(self, request):
        storage_client = get_storage_client()
        uploaded_file = request.FILES['file']
        
        # 生成存储名称
        storage_name = f"{generate_file_hash(uploaded_file)}{os.path.splitext(uploaded_file.name)[1]}"
        
        # 上传文件
        success = storage_client.upload_file(
            storage_name,
            uploaded_file,
            content_type=uploaded_file.content_type
        )
        
        if success:
            # 保存到数据库
            file_obj = File.objects.create(
                name=uploaded_file.name,
                storage_name=storage_name,
                size=uploaded_file.size,
                content_type=uploaded_file.content_type,
                owner=request.user
            )
            return Response(FileSerializer(file_obj).data, status=201)
        else:
            return Response({"error": "文件上传失败"}, status=500)
```

## 迁移指南

### 从MinIO迁移到OSS

1. **更新配置**：
   ```python
   STORAGE_TYPE = 'oss'
   ```

2. **配置OSS参数**：
   ```python
   OSS_CONFIG = {
       'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
       'ACCESS_KEY_ID': 'your_access_key_id',
       'ACCESS_KEY_SECRET': 'your_access_key_secret',
       'BUCKET_NAME': 'your_bucket_name',
       'REGION': 'cn-hangzhou'
   }
   ```

3. **重启应用**

### 数据迁移

如果需要将现有数据从MinIO迁移到OSS：

1. 使用MinIO客户端下载所有文件
2. 使用OSS客户端上传文件
3. 更新数据库中的文件路径（如果需要）

## 架构说明

### 存储抽象层

```
StorageBackend (抽象基类)
├── MinIOBackend (MinIO实现)
├── OSSBackend (阿里云OSS实现)
└── S3Backend (通用S3实现)
```

### 工厂模式

```python
StorageFactory.get_backend() -> StorageBackend
```

根据配置自动选择合适的存储后端。

## 配置说明

### 环境变量（推荐）

生产环境建议使用环境变量存储敏感信息：

```bash
export OSS_ACCESS_KEY_ID=your_access_key_id
export OSS_ACCESS_KEY_SECRET=your_access_key_secret
export OSS_BUCKET_NAME=your_bucket_name
```

然后在配置文件中：

```python
OSS_CONFIG = {
    'ENDPOINT': 'https://oss-cn-hangzhou.aliyuncs.com',
    'ACCESS_KEY_ID': os.environ.get('OSS_ACCESS_KEY_ID'),
    'ACCESS_KEY_SECRET': os.environ.get('OSS_ACCESS_KEY_SECRET'),
    'BUCKET_NAME': os.environ.get('OSS_BUCKET_NAME'),
    'REGION': 'cn-hangzhou'
}
```

### 不同环境的配置

- **开发环境**: 使用OSS内网Endpoint，更快的访问速度
- **生产环境**: 使用OSS公网Endpoint，确保可访问性
- **Docker环境**: 使用MinIO，便于本地开发和测试

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证Endpoint配置
   - 确认防火墙设置

2. **权限错误**
   - 检查AccessKey和SecretKey
   - 确认Bucket权限
   - 验证IAM策略

3. **Bucket不存在**
   - 创建Bucket
   - 检查Bucket名称
   - 确认地域配置

### 日志查看

存储操作的日志记录在 `logs/beancount-trans.log` 中：

```bash
tail -f logs/beancount-trans.log
```

### 测试连接

使用测试脚本验证配置：

```bash
python test_storage.py
```

## 性能优化

### OSS优化建议

1. **使用内网Endpoint**：如果在阿里云ECS上部署，使用内网Endpoint
2. **启用CDN**：对于静态文件，可以配置CDN加速
3. **合理设置分片大小**：大文件上传时设置合适的分片大小

### MinIO优化建议

1. **使用SSD存储**：提高I/O性能
2. **配置多节点**：提高可用性
3. **启用压缩**：减少存储空间

## 安全考虑

1. **访问控制**：使用最小权限原则
2. **加密传输**：启用HTTPS
3. **定期轮换密钥**：定期更新AccessKey
4. **审计日志**：启用访问日志记录

## 成本控制

### OSS成本

- **存储费用**：按实际存储量计费
- **流量费用**：按实际下载流量计费
- **请求费用**：按API调用次数计费

### 优化建议

1. **选择合适的存储类型**：根据访问频率选择标准存储或低频访问存储
2. **启用生命周期管理**：自动删除过期文件
3. **使用压缩**：减少存储空间和传输成本
