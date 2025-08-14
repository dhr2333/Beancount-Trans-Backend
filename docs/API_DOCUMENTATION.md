# Beancount-Trans API 文档

## 概述

Beancount-Trans 项目使用 **drf-spectacular** 来生成现代化的 API 文档。该文档基于 OpenAPI 3.0 规范，提供了完整的 API 接口说明。

## 访问方式

### 在线文档

1. **Swagger UI** (推荐)
   - 地址: `http://localhost:8000/api/docs/`
   - 特点: 交互式文档，可以直接在页面上测试 API

2. **ReDoc**
   - 地址: `http://localhost:8000/api/redoc/`
   - 特点: 更美观的文档展示，适合阅读

3. **OpenAPI Schema**
   - 地址: `http://localhost:8000/api/schema/`
   - 特点: 原始 JSON 格式的 API 规范

### 静态文档

生成静态文档文件：

```bash
# 生成 JSON 格式的文档
python manage.py generate_api_docs --output docs/api_schema.json

# 生成 YAML 格式的文档
python manage.py generate_api_docs --output docs/api_schema.yaml --format yaml
```

## API 分类

文档按功能模块分为以下几个标签：

- **认证**: 用户认证相关接口
- **文件管理**: 文件上传和管理接口
- **交易记录**: 交易记录管理接口
- **账户**: 账户管理接口
- **FAVA**: FAVA实例管理接口
- **翻译**: 交易记录翻译接口

## 认证方式

API 使用 JWT (JSON Web Token) 进行认证：

1. 获取 Token:
   ```
   POST /api/token/
   {
     "username": "your_username",
     "password": "your_password"
   }
   ```

2. 使用 Token:
   ```
   Authorization: Bearer <your_access_token>
   ```

3. 刷新 Token:
   ```
   POST /api/token/refresh/
   {
     "refresh": "<your_refresh_token>"
   }
   ```

## 主要接口

### 文件管理

- `GET /api/directories/` - 获取目录列表
- `POST /api/directories/` - 创建目录
- `GET /api/directories/{id}/contents/` - 获取目录内容
- `GET /api/directories/root_contents/` - 获取根目录内容

- `GET /api/files/` - 获取文件列表
- `POST /api/files/` - 上传文件
- `GET /api/files/{id}/` - 获取文件详情
- `DELETE /api/files/{id}/` - 删除文件

### 交易记录

- `GET /api/expense/` - 获取支出映射列表
- `POST /api/expense/` - 创建支出映射
- `PUT /api/expense/{id}/` - 更新支出映射
- `DELETE /api/expense/{id}/` - 删除支出映射

- `GET /api/assets/` - 获取资产映射列表
- `POST /api/assets/` - 创建资产映射
- `PUT /api/assets/{id}/` - 更新资产映射
- `DELETE /api/assets/{id}/` - 删除资产映射

- `GET /api/income/` - 获取收入映射列表
- `POST /api/income/` - 创建收入映射
- `PUT /api/income/{id}/` - 更新收入映射
- `DELETE /api/income/{id}/` - 删除收入映射

### 翻译服务

- `POST /api/translate/analyze/` - 分析文件内容
- `POST /api/translate/parse/` - 解析交易记录

### FAVA 服务

- `GET /api/fava/instances/` - 获取 FAVA 实例列表
- `POST /api/fava/instances/` - 创建 FAVA 实例
- `DELETE /api/fava/instances/{id}/` - 删除 FAVA 实例

## 错误处理

API 使用标准的 HTTP 状态码：

- `200` - 成功
- `201` - 创建成功
- `204` - 删除成功
- `400` - 请求错误
- `401` - 未认证
- `403` - 权限不足
- `404` - 资源不存在
- `500` - 服务器错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 开发说明

### 添加新的 API 文档

1. 在视图中添加 `@extend_schema` 装饰器：

```python
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(
        summary="获取列表",
        description="详细描述",
        tags=["标签名"],
        responses={200: YourSerializer(many=True)}
    ),
    create=extend_schema(
        summary="创建",
        description="详细描述",
        tags=["标签名"],
        request=YourSerializer,
        responses={201: YourSerializer}
    ),
)
class YourViewSet(ModelViewSet):
    # 视图实现
    pass
```

2. 在 `settings.py` 中添加新的标签：

```python
SPECTACULAR_SETTINGS = {
    # ... 其他配置
    'TAGS': [
        # ... 现有标签
        {'name': '新功能', 'description': '新功能模块的接口'},
    ],
}
```

### 自定义响应示例

```python
from drf_spectacular.utils import OpenApiExample

@extend_schema(
    examples=[
        OpenApiExample(
            '成功示例',
            value={
                'id': 1,
                'name': '示例名称',
                'created_at': '2024-01-01T00:00:00Z'
            },
            response_only=True,
            status_codes=['200']
        ),
    ]
)
def your_view(request):
    # 视图实现
    pass
```

## 部署说明

在生产环境中，建议：

1. 禁用调试模式的文档访问
2. 使用 HTTPS 访问文档
3. 配置适当的访问权限
4. 定期更新文档

## 故障排除

### 常见问题

1. **文档页面无法访问**
   - 检查 `drf_spectacular` 是否已安装
   - 确认 URL 配置正确
   - 检查 Django 服务是否正常运行

2. **API 接口未显示在文档中**
   - 确认视图使用了正确的装饰器
   - 检查序列化器是否正确配置
   - 验证 URL 路由是否正确

3. **认证问题**
   - 确认 JWT 配置正确
   - 检查认证类是否正确设置

### 调试命令

```bash
# 检查 schema 生成
python manage.py spectacular --file schema.json

# 验证 OpenAPI 规范
python manage.py spectacular --validate

# 生成静态文档
python manage.py generate_api_docs
```

## 相关链接

- [drf-spectacular 官方文档](https://drf-spectacular.readthedocs.io/)
- [OpenAPI 3.0 规范](https://swagger.io/specification/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)
