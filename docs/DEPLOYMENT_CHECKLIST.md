# 部署检查清单

本文档提供系统部署时的完整检查清单，确保所有功能正常工作。

## 部署前准备

- [ ] Python 环境已配置（推荐 Python 3.12+）
- [ ] 依赖包已安装（`pipenv install` 或 `pip install -r requirements.txt`）
- [ ] 数据库已配置（PostgreSQL/MySQL）
- [ ] Redis 已安装并运行（用于 Celery 和缓存）
- [ ] Celery 已配置

## 数据库初始化

### 1. 运行迁移

```bash
python manage.py migrate
```

**预期输出**: 所有迁移成功应用，无错误

**关键迁移**:
- `account_config.0005_*` - 账户模板系统
- `maps.0010_*` - 映射标签关联
- `translate.0005_*` - 格式化配置 AI 模型

### 2. 初始化官方模板

```bash
python manage.py init_official_templates
```

**预期输出**:
```
✓ 默认用户已存在: admin（或创建新用户）
✓ 创建官方账户模板: 中国用户标准账户模板 (66 个账户)
✓ 为 admin 用户创建了 85 个账户
✓ 创建官方支出映射模板 (30 项)
✓ 创建官方资产映射模板 (7 项)
✓ 创建官方收入映射模板 (2 项)
✓ 为 admin 用户创建映射: 支出=30, 资产=7, 收入=2
✓ admin 用户的格式化配置已存在
✓ 官方模板和默认用户初始化完成
```

## 功能验证

### 1. 验证 admin 用户数据

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from project.apps.account.models import Account, AccountTemplate
from project.apps.maps.models import Expense, Assets, Income, Template
from project.apps.translate.models import FormatConfig

User = get_user_model()
admin = User.objects.get(id=1)

# 应该输出 True
print(f"账户数量 > 0: {Account.objects.filter(owner=admin).count() > 0}")
print(f"支出映射 > 0: {Expense.objects.filter(owner=admin).count() > 0}")
print(f"资产映射 > 0: {Assets.objects.filter(owner=admin).count() > 0}")
print(f"格式化配置存在: {FormatConfig.objects.filter(owner=admin).exists()}")
print(f"官方账户模板: {AccountTemplate.objects.filter(is_official=True).count()}")
print(f"官方映射模板: {Template.objects.filter(is_official=True).count()}")
```

**预期结果**: 所有输出都应为 True 或正数

### 2. 验证 API 端点

启动服务器：
```bash
python manage.py runserver
```

访问以下端点（匿名访问）：

- [ ] `GET /api/account/` - 应返回 admin 用户的账户列表
- [ ] `GET /api/expense/` - 应返回 admin 用户的支出映射
- [ ] `GET /api/assets/` - 应返回 admin 用户的资产映射
- [ ] `GET /api/income/` - 应返回 admin 用户的收入映射
- [ ] `GET /api/account-templates/?is_official=true` - 应返回官方账户模板
- [ ] `GET /api/templates/?is_official=true` - 应返回官方映射模板
- [ ] `GET /api/config/` - 应返回 admin 用户的格式化配置

### 3. 测试账单解析

准备测试账单文件（支付宝 CSV），然后：

```bash
curl -X POST http://localhost:8000/api/translate/trans \
  -F "trans=@test_bill.csv" \
  -F "write=false" \
  -F "balance=false"
```

**预期结果**: 返回解析后的 Beancount 格式文本

### 4. 测试新用户注册

通过前端或 API 注册新用户，然后验证：

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from project.apps.account.models import Account
from project.apps.maps.models import Expense

User = get_user_model()
new_user = User.objects.get(username='新注册的用户名')

# 应该都有数据
print(f"账户: {Account.objects.filter(owner=new_user).count()}")
print(f"映射: {Expense.objects.filter(owner=new_user).count()}")
```

## Admin 后台验证

访问 `http://localhost:8000/admin/`

### 检查项

- [ ] 可以登录 admin 账户
- [ ] 看到 "账户模板" 管理菜单
- [ ] 看到 "映射模板" 管理菜单
- [ ] 看到 "格式化输出" 管理菜单
- [ ] 可以查看和编辑官方模板

## API 文档验证

访问 `http://localhost:8000/api/docs/`

- [ ] Swagger UI 正常显示
- [ ] 可以看到 account-templates 相关接口
- [ ] 可以看到 translate 相关接口
- [ ] 可以在线测试 API

## 性能检查

### 1. 数据量统计

```bash
python manage.py shell
```

```python
from project.apps.account.models import Account, AccountTemplate
from project.apps.maps.models import Template

print(f"官方账户模板项数: {AccountTemplate.objects.filter(is_official=True).first().items.count() if AccountTemplate.objects.filter(is_official=True).exists() else 0}")
print(f"官方映射模板总项数: {sum(t.items.count() for t in Template.objects.filter(is_official=True))}")
```

**预期值**:
- 官方账户模板项: 66
- 官方映射模板总项: 39

### 2. 新用户初始化性能

创建测试用户并记录时间：

```python
import time
from django.contrib.auth import get_user_model

User = get_user_model()

start = time.time()
user = User.objects.create_user(username='perf_test', password='test123')
end = time.time()

print(f"用户创建耗时: {end - start:.2f} 秒")
user.delete()
```

**预期时间**: < 2 秒

## 常见问题排查

### 问题 1: admin 用户不存在

```bash
python manage.py init_official_templates
```

### 问题 2: 官方模板为空

```bash
python manage.py init_official_templates --force
```

### 问题 3: 匿名用户无法访问数据

检查：
1. admin 用户（id=1）是否存在
2. admin 用户是否有数据
3. 权限配置是否正确（`AnonymousReadOnlyPermission`）

### 问题 4: 新用户没有获得初始数据

检查信号处理器是否已注册：

```python
# 检查 apps.py 中的 ready() 方法
# account/apps.py
def ready(self):
    import project.apps.account.signals

# maps/apps.py
def ready(self):
    import project.apps.maps.signals

# translate/apps.py
def ready(self):
    import project.apps.translate.signals
```

## 安全检查

- [ ] 生产环境中修改 admin 默认密码
- [ ] 设置合适的 CORS 策略
- [ ] 配置 HTTPS
- [ ] 限制 API 访问频率
- [ ] 配置文件上传大小限制

## 监控建议

### 日志监控

关注以下日志：
- 用户注册初始化日志（INFO 级别）
- 模板应用错误（ERROR 级别）
- 账单解析错误（ERROR 级别）

### 数据监控

定期检查：
- 官方模板完整性
- admin 用户数据完整性
- 新用户初始化成功率

## 备份建议

### 关键数据备份

1. **官方模板数据**
   ```bash
   python manage.py dumpdata account_config.AccountTemplate account_config.AccountTemplateItem -o backup_account_templates.json
   python manage.py dumpdata maps.Template maps.TemplateItem --natural-foreign --natural-primary -o backup_mapping_templates.json
   ```

2. **admin 用户数据**
   ```bash
   python manage.py dumpdata auth.User --pks=1 -o backup_admin_user.json
   python manage.py dumpdata account_config.Account maps.Expense maps.Assets maps.Income translate.FormatConfig --natural-foreign -o backup_admin_data.json
   ```

### 恢复数据

```bash
python manage.py loaddata backup_account_templates.json
python manage.py loaddata backup_mapping_templates.json
python manage.py loaddata backup_admin_user.json
python manage.py loaddata backup_admin_data.json
```

## 升级检查

升级系统时需要：

1. 备份数据库
2. 运行新的迁移
3. 检查官方模板版本
4. 如有更新，运行 `init_official_templates --force`
5. 验证系统功能

## 部署完成确认

全部检查通过后，系统应该：

✓ admin 用户完整配置
✓ 官方模板完整可用
✓ 匿名用户可以试用
✓ 新用户注册自动初始化
✓ 账单解析功能正常
✓ API 文档可访问
✓ Admin 后台可管理

系统已准备好为用户提供服务！

