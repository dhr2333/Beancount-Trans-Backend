# 案例文件功能说明

## 功能概述

本功能为新注册用户自动提供支付宝和微信的案例账单文件，帮助用户快速了解系统功能。

## 实现原理

### 文件引用机制
- 使用 `storage_name` 字段实现文件共享
- 相同内容的文件生成相同的哈希值作为 `storage_name`
- 多个用户引用同一个存储文件，避免重复存储

### 目录结构
```
案例文件/
├── 微信账单/
│   └── 完整测试_微信.csv
└── 支付宝账单/
    └── 完整测试_支付宝.csv
```

## 使用方法

### 1. 初始化 admin 用户的案例文件

```bash
# 首次运行，为 admin 用户创建案例文件
python manage.py init_official_templates

# 强制重新创建（如果已存在）
python manage.py init_official_templates --force
```

### 2. 新用户自动获得案例文件

新用户注册时会自动：
- 创建案例文件目录结构
- 引用 admin 用户的案例文件
- 创建对应的解析记录
- 生成对应的 .bean 文件

## 技术实现

### 1. 初始化命令 (`init_official_templates.py`)

- `_create_sample_files_for_admin()`: 为 admin 用户创建案例文件
- 从项目根目录读取案例文件
- 上传到存储系统
- 创建数据库记录和解析记录

### 2. 用户注册信号 (`signals.py`)

- `create_sample_files_for_new_user()`: 为新用户创建文件引用
- 自动创建目录结构
- 引用 admin 用户的案例文件
- 创建解析记录和 .bean 文件

### 3. 文件引用机制

- 使用相同的 `storage_name` 实现文件共享
- 删除文件时检查引用计数
- 只有没有其他引用时才删除存储文件

## 文件要求

### 案例文件位置
案例文件存放在 `fixtures/sample_files/` 目录：
- `fixtures/sample_files/完整测试_微信.csv`
- `fixtures/sample_files/完整测试_支付宝.csv`

### 文件格式
- 支持 CSV 格式
- 内容类型：`text/csv`
- 文件大小：无限制

## 测试

运行测试脚本验证功能：

```bash
python project/apps/file_manager/tests/test_sample_files.py
```

测试内容：
- admin 用户案例文件创建
- 新用户文件引用
- 文件引用机制

## 注意事项

1. **文件依赖**: 确保案例文件存在于 `fixtures/sample_files/` 目录
2. **admin 用户**: 需要 ID=1 的 admin 用户存在
3. **存储系统**: 需要配置好存储后端（MinIO/OSS/S3）
4. **权限**: 确保有文件读写权限

## 扩展功能

### 添加新的案例文件

1. 在 `_create_sample_files_for_admin()` 中添加新文件配置
2. 在 `create_sample_files_for_new_user()` 中添加对应的引用逻辑
3. 更新目录结构（如需要）

### 自定义目录结构

修改 `_create_sample_files_for_admin()` 和 `create_sample_files_for_new_user()` 中的目录创建逻辑。

## 故障排除

### 常见问题

1. **案例文件不存在**
   - 检查文件是否在 `fixtures/sample_files/` 目录
   - 确认文件名正确

2. **新用户没有案例文件**
   - 检查 admin 用户是否存在
   - 确认 admin 用户有案例文件
   - 检查信号是否正确注册

3. **文件上传失败**
   - 检查存储系统配置
   - 确认网络连接
   - 检查存储权限

### 调试方法

1. 查看 Django 日志
2. 运行测试脚本
3. 检查数据库记录
4. 验证存储系统状态
