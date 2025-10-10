# 管理员使用指南

## 概述

作为系统管理员，您的主要职责是维护**官方模板**，以确保所有匿名用户和新用户都能获得最佳的开箱即用体验。

## 核心原则

### 🎯 单一数据源

```
您只需维护一处：官方模板
    ↓
自动影响所有人：
  - 匿名用户（实时）
  - 新用户（注册时）
```

**注意**：您的个人账户（admin）数据与官方模板是分开的，修改官方模板不会影响您自己的数据。

---

## 日常维护任务

### 1. 维护官方支出映射

**访问路径**: Admin后台 → 映射模板 → "官方支出映射"

**操作步骤**:
1. 点击"官方支出映射"
2. 添加/修改模板项：
   - key: 商户关键字（如"蜜雪冰城"）
   - payee: 收款方名称（如"蜜雪冰城"）
   - account: 支出账户（选择已有账户）
   - currency: 货币（如"CNY"）
3. 保存

**常见场景**:
```
场景：用户反馈某个新商户无法识别
操作：
  1. 确认该商户的账单关键字
  2. 在官方支出映射中添加该商户
  3. 选择合适的支出账户
  4. 保存后立即生效
```

### 2. 维护官方资产映射

**访问路径**: Admin后台 → 映射模板 → "官方资产映射"

**操作步骤**:
1. 点击"官方资产映射"
2. 添加/修改模板项：
   - key: 支付方式关键字（如"余额"）
   - full: 完整名称（如"支付宝余额"）
   - account: 资产账户
3. 保存

**重要资产**:
- 支付宝余额、余额宝
- 微信零钱、零钱通
- 花呗、借呗

### 3. 维护官方账户模板

**访问路径**: Admin后台 → 账户模板 → "中国用户标准账户模板"

**操作步骤**:
1. 点击"中国用户标准账户模板"
2. 添加/修改账户模板项：
   - account_path: 账户路径（如"Expenses:Food:Snacks"）
   - enable: 默认启用状态
3. 保存

**注意事项**:
- 遵循 Beancount 账户命名规范
- 保持账户层级关系合理
- 新增子账户会自动创建父账户

---

## 高级操作

### 批量更新模板

如果需要大量修改，推荐使用管理命令：

```bash
# 1. 编辑文件
vim project/apps/account/management/commands/init_official_templates.py

# 找到 expense_mappings、assets_mappings 等列表
# 修改或添加映射项

# 2. 重新生成
python manage.py init_official_templates --force

# 3. 验证
python check_system_status.py
```

### 创建新的官方模板

如果您想创建不同地区或行业的官方模板：

```bash
# 在 Admin 后台
1. 创建新模板
2. 设置 is_official=True
3. 添加模板项
4. 设置版本号

# 新用户注册时会自动应用所有官方模板
```

### 模板版本管理

更新模板时建议：

```bash
# 1. 增加版本号
version: "1.0.0" → "1.1.0"

# 2. 添加更新说明
update_notes: "新增10个常用商户映射，优化交通类别账户"

# 3. 保存后发布公告
# 用户可以查看版本历史并选择应用
```

---

## 监控和分析

### 检查系统状态

```bash
python check_system_status.py
```

输出示例：
```
✓ 默认用户: admin
【官方模板】
  账户模板: 1 个
  映射模板: 3 个
【admin 用户数据】
  账户: 85
  映射: 39
  配置: BERT
```

### 查看模板使用情况

```bash
python manage.py shell
```

```python
from project.apps.maps.models import Template, Expense
from django.contrib.auth import get_user_model

User = get_user_model()

# 统计使用官方模板的用户数（无自己数据的用户）
users_using_templates = User.objects.filter(
    expense__isnull=True
).distinct().count()

print(f"使用官方模板的用户数: {users_using_templates}")

# 查看官方模板内容
official_template = Template.objects.filter(
    name='官方支出映射'
).first()

print(f"官方支出映射项数: {official_template.items.count()}")
for item in official_template.items.all()[:5]:
    print(f"  - {item.key} → {item.account.account}")
```

---

## 常见维护场景

### 场景 1：添加新商户

**用户反馈**: "我在XX奶茶店消费，系统没有识别"

**操作**:
```
1. 在 Admin 后台找到"官方支出映射"
2. 添加新项：
   - key: "XX奶茶"
   - payee: "XX奶茶"
   - account: Expenses:Food:DrinkFruit
   - currency: CNY
3. 保存
4. 通知用户可以重新解析账单
```

### 场景 2：调整账户分类

**需求**: "将所有饮品店归类到 Expenses:Food:Beverages"

**操作**:
```
1. 在账户模板中添加新账户：
   Expenses:Food:Beverages

2. 在支出映射中批量更新饮品店：
   - 找到所有饮品店映射
   - 修改 account 为新账户
   - 保存

3. 重新应用模板到 admin 用户：
   python manage.py init_official_templates --force
```

### 场景 3：删除过时映射

**需求**: "某个商户已关闭，移除映射"

**操作**:
```
1. 在"官方支出映射"中找到该项
2. 删除
3. 保存（立即对匿名用户生效）
```

### 场景 4：支持新的支付方式

**需求**: "支持抖音支付"

**操作**:
```
1. 在账户模板中添加：
   Assets:Savings:Web:DouYinPay

2. 在资产映射中添加：
   - key: "抖音支付"
   - full: "抖音支付"
   - account: Assets:Savings:Web:DouYinPay

3. 保存
```

---

## 故障排查

### 问题 1：匿名用户解析失败

**检查**:
```bash
# 1. 验证官方模板存在
python manage.py shell -c "
from project.apps.maps.models import Template
print(Template.objects.filter(is_official=True).count())
"
# 应该输出: 3 或更多

# 2. 验证模板有数据
python manage.py shell -c "
from project.apps.maps.models import Template
for t in Template.objects.filter(is_official=True):
    print(f'{t.name}: {t.items.count()} 项')
"
# 每个模板都应该有数据
```

**解决**:
```bash
python manage.py init_official_templates --force
```

### 问题 2：新商户添加后不生效

**原因**: 可能添加到了自己的映射而不是官方模板

**检查**:
```
在 Admin 后台查看该映射的:
- 所属模板是否为"官方XX映射"
- is_official 是否为 True
```

### 问题 3：账户引用错误

**现象**: 添加映射项时找不到账户

**原因**: 账户不存在或被禁用

**解决**:
```
1. 先在账户模板中添加所需账户
2. 运行 init_official_templates --force
3. 再添加映射项
```

---

## 最佳实践

### DO ✅

1. **定期审查**: 每月审查官方模板，添加常用商户
2. **版本管理**: 重大更新时增加版本号并记录
3. **测试验证**: 修改后创建测试用户验证
4. **备份数据**: 定期备份官方模板
5. **收集反馈**: 关注用户的映射匹配失败情况

### DON'T ❌

1. ❌ 不要删除核心账户（如 Expenses:Food）
2. ❌ 不要在官方模板中添加个人特定映射
3. ❌ 不要直接修改数据库
4. ❌ 不要忘记保存修改
5. ❌ 不要在生产环境直接测试

---

## 快速参考

### 常用命令

```bash
# 初始化/重建官方模板
python manage.py init_official_templates --force

# 检查系统状态
python check_system_status.py

# 备份官方模板
python manage.py dumpdata account_config.AccountTemplate account_config.AccountTemplateItem maps.Template maps.TemplateItem --natural-foreign -o templates_backup.json

# 恢复官方模板
python manage.py loaddata templates_backup.json
```

### 常用查询

```python
# 查看官方模板
from project.apps.maps.models import Template
Template.objects.filter(is_official=True)

# 查看无数据的用户数（使用官方模板的用户）
from django.contrib.auth import get_user_model
from project.apps.maps.models import Expense
User = get_user_model()
User.objects.filter(expense__isnull=True).count()

# 查看最近注册的用户的数据情况
recent_user = User.objects.latest('date_joined')
Expense.objects.filter(owner=recent_user).count()
```

---

## 支持和联系

如有问题或建议，请：
- 查看文档：[docs/](../docs/)
- 提交 Issue
- 联系开发团队

祝您维护顺利！👍

