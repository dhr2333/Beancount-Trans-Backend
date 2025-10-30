# Authentication 应用

提供手机号认证、多账号绑定等用户认证功能。

## 功能特性

### 1. 手机号认证
- ✅ 手机号 + 密码登录
- ✅ 手机号 + 验证码登录
- ✅ 手机号注册
- ✅ 验证码发送（阿里云短信服务）
- ✅ 验证码频率限制（60秒/次）
- ✅ 验证码有效期（5分钟）

### 2. 多账号绑定
- ✅ 支持多种登录方式绑定到同一用户
  - 手机号
  - GitHub OAuth
  - Google OAuth
  - 用户名密码
- ✅ 账号绑定/解绑管理
- ✅ 至少保留一种登录方式的安全限制

### 3. 用户信息管理
- ✅ 获取用户完整信息
- ✅ 更新用户信息
- ✅ 查看绑定的账号列表

## 技术栈

- **手机号字段**: `django-phonenumber-field` + `phonenumbers`
- **短信服务**: 阿里云短信服务 (支持模拟模式)
- **缓存**: Redis (验证码存储)
- **认证**: Django 认证后端 + JWT

## 模块结构

```
authentication/
├── __init__.py
├── apps.py                 # 应用配置
├── models.py               # UserProfile 模型
├── admin.py                # 管理后台配置
├── signals.py              # 信号处理（自动创建 UserProfile）
├── backends.py             # 认证后端（密码/验证码）
├── sms.py                  # 阿里云短信服务
├── serializers.py          # API 序列化器
├── views.py                # API 视图
├── urls.py                 # URL 路由
├── migrations/             # 数据库迁移
├── tests/                  # 单元测试
│   ├── test_phone_authentication.py
│   ├── test_account_binding.py
│   └── test_sms_service.py
└── README.md              # 本文档
```

## 数据模型

### UserProfile
扩展 Django User 模型的用户信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| user | OneToOne(User) | 关联的用户 |
| phone_number | PhoneNumberField | 手机号（E164格式） |
| phone_verified | BooleanField | 手机号是否已验证 |
| created | DateTimeField | 创建时间 |
| modified | DateTimeField | 修改时间 |

## API 端点

### 手机号认证
- `POST /api/auth/phone/send-code/` - 发送验证码
- `POST /api/auth/phone/login-by-code/` - 验证码登录
- `POST /api/auth/phone/login-by-password/` - 密码登录
- `POST /api/auth/phone/register/` - 手机号注册

### 账号绑定
- `GET /api/auth/bindings/list/` - 获取绑定信息
- `POST /api/auth/bindings/bind-phone/` - 绑定手机号
- `DELETE /api/auth/bindings/unbind-phone/` - 解绑手机号
- `DELETE /api/auth/bindings/unbind-social/{provider}/` - 解绑社交账号

### 用户信息
- `GET /api/auth/profile/me/` - 获取用户信息
- `PATCH /api/auth/profile/update_me/` - 更新用户信息

详细 API 文档请参阅: [PHONE_AUTHENTICATION_API.md](../../../docs/PHONE_AUTHENTICATION_API.md)

## 配置说明

### settings.py 配置

```python
# 安装应用
INSTALLED_APPS = [
    ...
    'phonenumber_field',
    'project.apps.authentication',
    ...
]

# 认证后端
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'project.apps.authentication.backends.PhonePasswordBackend',
    'project.apps.authentication.backends.PhoneCodeBackend',
]

# 阿里云短信配置
ALIYUN_SMS_ACCESS_KEY_ID = os.environ.get('ALIYUN_SMS_ACCESS_KEY_ID', '')
ALIYUN_SMS_ACCESS_KEY_SECRET = os.environ.get('ALIYUN_SMS_ACCESS_KEY_SECRET', '')
ALIYUN_SMS_SIGN_NAME = os.environ.get('ALIYUN_SMS_SIGN_NAME', '')
ALIYUN_SMS_TEMPLATE_CODE = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE', '')

# 短信验证码配置
SMS_CODE_EXPIRE_SECONDS = 300  # 5分钟
SMS_CODE_RESEND_INTERVAL = 60  # 1分钟

# Phonenumber Field
PHONENUMBER_DEFAULT_REGION = 'CN'
PHONENUMBER_DB_FORMAT = 'E164'
```

### 环境变量配置

```bash
# 阿里云短信服务（可选，不配置则使用模拟模式）
ALIYUN_SMS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_SMS_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_SMS_SIGN_NAME=your_sign_name
ALIYUN_SMS_TEMPLATE_CODE=SMS_123456789
```

## 使用指南

### 1. 安装依赖

```bash
pip install django-phonenumber-field phonenumbers
pip install aliyun-python-sdk-core aliyun-python-sdk-dysmsapi
```

### 2. 运行数据库迁移

```bash
python manage.py makemigrations authentication
python manage.py migrate
```

### 3. 创建超级用户

```bash
python manage.py createsuperuser
```

### 4. 测试 API

```bash
# 运行测试
pytest project/apps/authentication/tests/

# 运行特定测试
pytest project/apps/authentication/tests/test_phone_authentication.py
```

## 短信服务说明

### 模拟模式
开发环境下，如果未配置阿里云短信服务，系统会自动启用模拟模式：
- 验证码会在日志中输出
- 所有发送操作都会返回成功
- 验证码仍然会正常存储到 Redis

### 生产模式
生产环境需要配置真实的阿里云短信服务：
1. 在阿里云控制台开通短信服务
2. 创建短信签名和模板
3. 配置环境变量
4. 短信模板需包含 `${code}` 参数

## 安全特性

1. **验证码安全**
   - 验证码存储在 Redis，不会持久化到数据库
   - 5分钟有效期
   - 使用后立即销毁
   - 发送频率限制（60秒）

2. **手机号唯一性**
   - 数据库层面保证手机号唯一
   - 绑定前检查是否已被占用

3. **登录方式保护**
   - 解绑时确保至少保留一种登录方式
   - 防止用户完全失去账号访问权限

4. **密码安全**
   - 使用 Django 内置密码验证器
   - 密码哈希存储

## 开发注意事项

1. **手机号格式**
   - 统一使用 E164 格式存储 (+8613800138000)
   - API 接受多种格式输入 (+86/无前缀)

2. **验证码存储**
   - Key 格式: `sms:code:{phone_number}`
   - 重发限制 Key: `sms:resend:{phone_number}`

3. **Signal 处理**
   - 用户创建时自动创建 UserProfile
   - 使用 post_save 信号确保数据一致性

4. **测试**
   - 所有测试使用 pytest
   - Mock 阿里云短信服务
   - 清理 Redis 缓存

## 故障排查

### 1. 验证码发送失败
- 检查阿里云配置是否正确
- 查看日志确认错误信息
- 确认短信模板是否审核通过

### 2. 手机号格式错误
- 确认使用 E164 格式
- 检查国家代码是否正确

### 3. 验证码验证失败
- 确认验证码未过期
- 检查 Redis 连接是否正常
- 确认验证码未被使用过

### 4. 绑定失败
- 检查手机号是否已被占用
- 确认验证码验证通过
- 查看日志了解详细错误

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 编写测试
4. 提交 Pull Request

## 许可证

与主项目相同

