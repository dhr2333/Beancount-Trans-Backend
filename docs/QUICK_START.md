# 快速开始指南

## 系统初始化

### 首次部署

1. **运行数据库迁移**
   ```bash
   python manage.py migrate
   ```

2. **初始化官方模板和默认用户**
   ```bash
   python manage.py init_official_templates
   ```
   
   此命令会：
   - 创建 admin 用户（id=1，密码: admin123456）
   - 创建官方账户模板（66 个标准账户）
   - 创建官方映射模板（支出30项、资产7项、收入2项）
   - 为 admin 用户应用所有模板
   - 创建格式化配置

3. **验证初始化**
   ```bash
   # 检查 admin 用户数据
   python manage.py shell -c "
   from django.contrib.auth import get_user_model
   from project.apps.account.models import Account
   from project.apps.maps.models import Expense, Assets, Income
   
   User = get_user_model()
   admin = User.objects.get(id=1)
   
   print(f'账户数量: {Account.objects.filter(owner=admin).count()}')
   print(f'支出映射: {Expense.objects.filter(owner=admin).count()}')
   print(f'资产映射: {Assets.objects.filter(owner=admin).count()}')
   print(f'收入映射: {Income.objects.filter(owner=admin).count()}')
   "
   ```

## 用户使用流程

### 新用户注册

用户通过前端注册后，系统自动：
1. 创建用户账户
2. 应用官方账户模板（85个账户，包含自动创建的父账户）
3. 应用官方映射模板（39个映射）
4. 创建默认格式化配置

**无需手动配置，即可开始解析账单**

### 匿名用户试用

匿名用户可以：
1. 访问 admin 用户的账户和映射数据（只读）
2. 上传账单进行解析
3. 查看解析结果
4. **无法保存或修改数据**

示例：
```bash
# 匿名用户访问账户列表
curl http://localhost:8000/api/account/

# 匿名用户解析账单（使用 admin 用户的映射）
curl -X POST http://localhost:8000/api/translate/trans \
  -F "trans=@alipay_bill.csv" \
  -F "write=false"
```

## 模板管理

### 查看官方模板

```bash
# 查看官方账户模板
curl http://localhost:8000/api/account-templates/?is_official=true

# 查看官方映射模板
curl http://localhost:8000/api/templates/?is_official=true
```

### 应用模板到自己的账户

```bash
# 应用官方账户模板
POST /api/account-templates/1/apply/
{
    "action": "merge",
    "conflict_resolution": "skip"
}

# 应用官方支出映射模板
POST /api/templates/1/apply/
{
    "action": "merge",
    "conflict_resolution": "skip"
}
```

### 创建自定义模板

用户可以：
1. 在 Admin 后台创建模板
2. 通过 API 创建模板
3. 设置模板为公开，分享给其他用户

## 数据流程

### 账单解析流程

```
用户上传账单
  ↓
1. 识别账单类型（支付宝/微信/银行）
  ↓
2. 提取交易记录
  ↓
3. 使用用户的映射数据进行匹配
   - 登录用户: 使用自己的映射
   - 匿名用户: 使用 admin 用户的映射
  ↓
4. 使用用户的账户数据
   - 登录用户: 使用自己的账户
   - 匿名用户: 使用 admin 用户的账户
  ↓
5. 使用用户的格式化配置
   - 登录用户: 使用自己的配置
   - 匿名用户: 使用 admin 用户的配置
  ↓
6. 生成 Beancount 格式文本
```

## 常见问题

### Q1: 如何更新官方模板？

A: 编辑 `init_official_templates.py`，然后运行：
```bash
python manage.py init_official_templates --force
```

注意：这只会更新官方模板本身，不会影响现有用户的数据。

### Q2: 现有用户如何获取最新官方模板？

A: 用户可以通过 API 手动应用最新的官方模板：
```bash
POST /api/account-templates/{template_id}/apply/
{
    "action": "merge",
    "conflict_resolution": "skip"
}
```

### Q3: 匿名用户能保存数据吗？

A: 不能。匿名用户只有只读权限，无法：
- 创建或修改账户
- 创建或修改映射
- 保存解析结果到文件
- 修改格式化配置

### Q4: 如何为特定用户自定义映射？

A: 用户登录后可以：
1. 直接在 Admin 或 API 中添加/修改映射
2. 创建自己的模板
3. 应用其他用户的公开模板

### Q5: admin 用户数据丢失怎么办？

A: 重新运行初始化命令：
```bash
python manage.py init_official_templates --force
```

## 技术架构

### 模板系统设计

```
┌─────────────────┐
│ AccountTemplate │ (账户模板)
├─────────────────┤
│ - 独立模板系统  │
│ - 树形账户结构  │
└─────────────────┘

┌─────────────────┐
│ Template        │ (映射模板)
├─────────────────┤
│ - 三种类型      │
│ - expense       │
│ - income        │
│ - assets        │
└─────────────────┘

┌─────────────────┐
│ FormatConfig    │ (格式化配置)
├─────────────────┤
│ - 单一配置记录  │
│ - 自动创建默认值│
└─────────────────┘
```

### 信号处理流程

```
用户注册 (user_signed_up)
  ├─→ account/signals.py
  │    └─→ 应用官方账户模板
  │
  ├─→ maps/signals.py
  │    └─→ 应用官方映射模板
  │         ├─→ expense
  │         ├─→ income
  │         └─→ assets
  │
  └─→ translate/signals.py
       └─→ 创建格式化配置
```

## 下一步

- 查看 [模板系统架构文档](TEMPLATE_SYSTEM.md) 了解详细技术细节
- 查看 [API 文档](API_DOCUMENTATION.md) 了解完整 API 接口
- 访问 Admin 后台管理模板: http://localhost:8000/admin/

