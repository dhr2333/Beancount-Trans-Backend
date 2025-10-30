# 手机号认证 API 文档

本文档说明如何使用手机号登录、注册和账号绑定功能。

## 目录
- [手机号认证](#手机号认证)
  - [发送验证码](#发送验证码)
  - [验证码登录](#验证码登录)
  - [密码登录](#密码登录)
  - [手机号注册](#手机号注册)
- [账号绑定管理](#账号绑定管理)
  - [获取绑定信息](#获取绑定信息)
  - [绑定手机号](#绑定手机号)
  - [解绑手机号](#解绑手机号)
  - [解绑社交账号](#解绑社交账号)
- [用户信息管理](#用户信息管理)
  - [获取用户信息](#获取用户信息)
  - [更新用户信息](#更新用户信息)

---

## 手机号认证

### 发送验证码

发送短信验证码到指定手机号。

**请求**
```http
POST /api/auth/phone/send-code/
Content-Type: application/json

{
  "phone_number": "+8613800138000"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| phone_number | string | 是 | 手机号，支持 E164 格式（+8613800138000）或纯数字（13800138000） |

**响应示例**
```json
{
  "message": "验证码已发送",
  "phone_number": "+8613800138000"
}
```

**限制**
- 同一手机号 60 秒内只能发送一次
- 验证码有效期为 5 分钟

---

### 验证码登录

使用手机号和验证码登录。

**请求**
```http
POST /api/auth/phone/login-by-code/
Content-Type: application/json

{
  "phone_number": "+8613800138000",
  "code": "123456"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| phone_number | string | 是 | 手机号 |
| code | string | 是 | 6位数字验证码 |

**响应示例**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone_number": "+8613800138000"
  }
}
```

---

### 密码登录

使用手机号和密码登录。

**请求**
```http
POST /api/auth/phone/login-by-password/
Content-Type: application/json

{
  "phone_number": "+8613800138000",
  "password": "your_password"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| phone_number | string | 是 | 手机号 |
| password | string | 是 | 密码 |

**响应示例**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone_number": "+8613800138000"
  }
}
```

---

### 手机号注册

使用手机号和验证码注册新账号。

**请求**
```http
POST /api/auth/phone/register/
Content-Type: application/json

{
  "phone_number": "+8613800138000",
  "code": "123456",
  "username": "newuser",
  "password": "SecurePass123!",
  "email": "newuser@example.com"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| phone_number | string | 是 | 手机号 |
| code | string | 是 | 6位数字验证码 |
| username | string | 是 | 用户名（3-150字符） |
| password | string | 是 | 密码（需符合密码强度要求） |
| email | string | 否 | 邮箱（可选） |

**响应示例**
```json
{
  "message": "注册成功",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 2,
    "username": "newuser",
    "email": "newuser@example.com",
    "phone_number": "+8613800138000"
  }
}
```

**注意**
- 注册成功后自动登录并返回 JWT token
- 手机号会自动标记为已验证
- 注册后会自动应用官方账户模板和映射模板

---

## 账号绑定管理

### 获取绑定信息

获取当前用户的所有绑定信息。

**请求**
```http
GET /api/auth/bindings/list/
Authorization: Bearer <access_token>
```

**响应示例**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "phone_number": "+8613800138000",
  "phone_verified": true,
  "social_accounts": [
    {
      "provider": "github",
      "uid": "12345678",
      "extra_data": {
        "login": "testuser",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678"
      },
      "date_joined": "2024-01-01T10:00:00Z"
    }
  ],
  "has_password": true
}
```

---

### 绑定手机号

为当前用户绑定手机号。

**请求**
```http
POST /api/auth/bindings/bind-phone/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "phone_number": "+8613800138000",
  "code": "123456"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| phone_number | string | 是 | 手机号 |
| code | string | 是 | 6位数字验证码 |

**响应示例**
```json
{
  "message": "手机号绑定成功",
  "phone_number": "+8613800138000"
}
```

**注意**
- 手机号必须先发送验证码
- 一个手机号只能绑定一个用户
- 绑定成功后手机号自动标记为已验证

---

### 解绑手机号

解绑当前用户的手机号。

**请求**
```http
DELETE /api/auth/bindings/unbind-phone/
Authorization: Bearer <access_token>
```

**响应示例**
```json
{
  "message": "手机号解绑成功"
}
```

**注意**
- 至少保留一种登录方式（手机号、密码或社交账号）
- 如果这是唯一的登录方式，解绑会失败

---

### 解绑社交账号

解绑指定的社交账号。

**请求**
```http
DELETE /api/auth/bindings/unbind-social/{provider}/
Authorization: Bearer <access_token>
```

**路径参数**
| 参数 | 说明 |
|------|------|
| provider | 社交账号提供商：`github` 或 `google` |

**响应示例**
```json
{
  "message": "github 账号解绑成功"
}
```

**注意**
- 至少保留一种登录方式
- 如果这是唯一的登录方式，解绑会失败

---

## 用户信息管理

### 获取用户信息

获取当前用户的详细信息。

**请求**
```http
GET /api/auth/profile/me/
Authorization: Bearer <access_token>
```

**响应示例**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "phone_number": "+8613800138000",
  "phone_verified": true,
  "date_joined": "2024-01-01T10:00:00Z",
  "last_login": "2024-01-15T15:30:00Z",
  "created": "2024-01-01T10:00:00Z",
  "modified": "2024-01-15T15:30:00Z"
}
```

---

### 更新用户信息

更新当前用户的信息。

**请求**
```http
PATCH /api/auth/profile/update_me/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com"
}
```

**参数说明**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| email | string | 否 | 新邮箱地址 |

**响应示例**
```json
{
  "username": "testuser",
  "email": "newemail@example.com",
  "phone_number": "+8613800138000",
  "phone_verified": true,
  "date_joined": "2024-01-01T10:00:00Z",
  "last_login": "2024-01-15T15:30:00Z",
  "created": "2024-01-01T10:00:00Z",
  "modified": "2024-01-15T15:35:00Z"
}
```

---

## 使用示例

### JavaScript/前端示例

```javascript
// 1. 发送验证码
async function sendCode(phoneNumber) {
  const response = await fetch('/api/auth/phone/send-code/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber })
  });
  return await response.json();
}

// 2. 验证码登录
async function loginByCode(phoneNumber, code) {
  const response = await fetch('/api/auth/phone/login-by-code/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber, code: code })
  });
  const data = await response.json();
  
  // 保存 token
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  
  return data;
}

// 3. 获取用户信息
async function getUserInfo() {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/auth/profile/me/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
}

// 4. 绑定手机号
async function bindPhone(phoneNumber, code) {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/auth/bindings/bind-phone/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ phone_number: phoneNumber, code: code })
  });
  return await response.json();
}
```

### Python/测试示例

```python
import requests

BASE_URL = 'http://localhost:8000'

# 1. 发送验证码
response = requests.post(f'{BASE_URL}/api/auth/phone/send-code/', json={
    'phone_number': '+8613800138000'
})
print(response.json())

# 2. 手机号注册
response = requests.post(f'{BASE_URL}/api/auth/phone/register/', json={
    'phone_number': '+8613800138000',
    'code': '123456',
    'username': 'newuser',
    'password': 'SecurePass123!',
    'email': 'newuser@example.com'
})
data = response.json()
access_token = data['access']

# 3. 获取用户信息
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(f'{BASE_URL}/api/auth/profile/me/', headers=headers)
print(response.json())

# 4. 获取绑定信息
response = requests.get(f'{BASE_URL}/api/auth/bindings/list/', headers=headers)
print(response.json())
```

---

## 错误代码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功（注册） |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 常见错误

### 验证码相关
- `发送过于频繁，请60秒后再试` - 需要等待后重试
- `验证码错误或已过期` - 验证码不正确或超过5分钟有效期

### 注册相关
- `用户名已存在` - 需要更换用户名
- `该手机号已被注册` - 手机号已被其他用户使用

### 绑定相关
- `该手机号已被其他用户绑定` - 手机号已被占用
- `无法解绑，请至少保留一种登录方式` - 需要先绑定其他登录方式

---

## 安全建议

1. **使用 HTTPS**：生产环境必须使用 HTTPS 传输
2. **Token 存储**：建议将 JWT token 存储在 httpOnly cookie 中
3. **验证码限制**：服务端已实现发送频率限制（60秒）和有效期（5分钟）
4. **密码强度**：建议使用大小写字母、数字和特殊字符组合
5. **多账号绑定**：建议用户绑定多种登录方式，防止单一方式失效

