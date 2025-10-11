# 模板系统架构文档

## 概述

本系统实现了统一的模板管理机制，为新用户提供开箱即用的账户、映射和配置数据。模板系统包含三个核心部分：

1. **账户模板**（Account Templates）- 管理 Beancount 账户结构
2. **映射模板**（Mapping Templates）- 管理支出/收入/资产映射
3. **格式化配置**（Format Config）- 管理账单格式化输出配置

## 一、模板类型

### 1. 账户模板（Account Templates）

**所属应用**: `account`

**模型结构**:
- `AccountTemplate` - 账户模板主表
- `AccountTemplateItem` - 账户模板项（每项包含一个账户路径）

**特性**:
- 支持官方/公开/私有模板
- 支持版本管理
- 新用户注册时自动应用官方模板

**API 端点**:
- `GET /api/account-templates/` - 获取模板列表
- `POST /api/account-templates/` - 创建模板
- `GET /api/account-templates/{id}/` - 获取模板详情
- `PUT/PATCH /api/account-templates/{id}/` - 更新模板
- `DELETE /api/account-templates/{id}/` - 删除模板
- `POST /api/account-templates/{id}/apply/` - 应用模板到当前用户

### 2. 映射模板（Mapping Templates）

**所属应用**: `maps`

**模型结构**:
- `Template` - 映射模板主表（区分 expense/income/assets 三种类型）
- `TemplateItem` - 映射模板项

**特性**:
- 支持三种映射类型（支出/收入/资产）
- 支持官方/公开/私有模板
- 支持版本管理
- 新用户注册时自动应用官方模板

**API 端点**:
- `GET /api/templates/` - 获取模板列表
- `POST /api/templates/` - 创建模板
- `GET /api/templates/{id}/` - 获取模板详情
- `PUT/PATCH /api/templates/{id}/` - 更新模板
- `DELETE /api/templates/{id}/` - 删除模板
- `POST /api/templates/{id}/apply/` - 应用模板到当前用户

### 3. 格式化配置（Format Config）

**所属应用**: `translate`

**模型结构**:
- `FormatConfig` - 用户格式化配置（每用户一条记录）

**特性**:
- 每个用户一条配置记录
- 自动创建默认配置
- 支持自定义 AI 模型、货币、显示选项等

**API 端点**:
- `GET /api/config/` - 获取当前用户配置
- `PUT/PATCH /api/config/` - 更新当前用户配置

## 二、初始化流程

### 新用户注册时的自动初始化

当用户通过 `allauth` 注册时，会触发 `user_signed_up` 信号，自动完成以下初始化：

```
用户注册
  ↓
触发 user_signed_up 信号
  ↓
1. account/signals.py - 应用官方账户模板
  ↓
2. maps/signals.py - 应用官方映射模板
  ↓
3. translate/signals.py - 创建格式化配置
  ↓
初始化完成
```

**初始化数据量**:
- 账户: ~85 个（包含自动创建的父账户）
- 支出映射: ~30 个
- 资产映射: ~7 个
- 收入映射: ~2 个
- 格式化配置: 1 个

### 手动初始化（管理员操作）

运行以下命令初始化官方模板和 admin 用户（id=1）：

```bash
python manage.py init_official_templates
```

**选项**:
- `--skip-admin` - 跳过创建 admin 用户
- `--force` - 强制重建官方模板（删除现有）

**执行内容**:
1. 确保 id=1 的 admin 用户存在
2. 创建官方账户模板
3. 应用官方账户模板到 admin 用户
4. 创建官方映射模板（支出/资产/收入）
5. 应用官方映射模板到 admin 用户
6. 确保 admin 用户有格式化配置

## 三、匿名用户访问

### 设计理念

匿名用户可以访问 admin（id=1）用户的数据，实现开箱即用的解析功能。

### 实现方式

各应用的视图集中均实现了匿名用户过滤逻辑：

**account/views.py**:
```python
def get_queryset(self):
    if self.request.user.is_authenticated:
        queryset = queryset.filter(owner=self.request.user)
    else:
        # 匿名用户使用 id=1 用户的数据
        default_user = User.objects.get(id=1)
        queryset = queryset.filter(owner=default_user)
```

**权限控制**:
- 匿名用户: 只读访问 admin 用户数据
- 登录用户: 读写自己的数据
- 使用权限类: `AnonymousReadOnlyPermission`

## 四、模板维护

### 官方模板更新流程

1. **修改模板定义**
   - 编辑 `init_official_templates.py` 中的模板数据
   - 更新版本号

2. **重新生成模板**
   ```bash
   python manage.py init_official_templates --force
   ```

3. **推送到生产环境**
   - 新注册用户自动获得最新模板
   - 现有用户不受影响（可选择手动应用新模板）

### 用户自定义模板

用户可以：
1. 在 Admin 或 API 中创建自己的模板
2. 设置模板为公开，分享给其他用户
3. 应用其他用户的公开模板

## 五、官方模板内容

### 账户模板（66个账户）

**资产账户**:
- `Assets:Savings:Web:*` - 网络支付账户（支付宝、微信等）
- `Assets:Savings:Bank:*` - 银行储蓄卡账户
- `Assets:Savings:Recharge:*` - 储值账户
- `Assets:Receivables:Personal` - 应收账款

**负债账户**:
- `Liabilities:CreditCard:Bank:*` - 银行信用卡
- `Liabilities:CreditCard:Web:*` - 网络信用账户（花呗、抖音月付等）
- `Liabilities:Payables:Personal` - 应付账款

**权益账户**:
- `Equity:OpenBalance` - 期初余额
- `Equity:Adjustments` - 调整

**收入账户**:
- `Income:Active:*` - 主动收入（工资、奖金）
- `Income:Investment:*` - 投资收入
- `Income:Sideline:*` - 副业收入
- `Income:Business` - 业务收入
- `Income:Receivables:*` - 应收账款（红包、转账）
- `Income:Discount` - 优惠折扣

**支出账户**:
- `Expenses:Food:*` - 餐饮（早/午/晚餐、饮品）
- `Expenses:TransPort:*` - 交通（公共/私人）
- `Expenses:Shopping:*` - 购物（数码、服饰、美妆、母婴）
- `Expenses:Health:*` - 医疗健康
- `Expenses:Culture:*` - 文化娱乐
- `Expenses:Home:*` - 家居生活
- `Expenses:Finance:*` - 金融费用
- `Expenses:Government:*` - 政府税费

### 支出映射模板（30项）

常用商户映射，如：
- 饮品店: 蜜雪冰城、古茗、喜茶、茶百道、一点点、霸王茶姬、瑞幸等
- 餐饮店: 肯德基、华莱士、塔斯汀等
- 外卖平台: 饿了么、美团
- 购物平台: 淘宝、京东、拼多多、得物
- 交通相关: 停车、充电、加油、ETC、地铁、12306
- 医疗相关: 药房、药店、医院

### 资产映射模板（7项）

常用支付方式映射：
- 支付宝: 余额、余额宝、花呗
- 微信: 零钱、零钱通

### 收入映射模板（2项）

常用收入类型：
- 红包
- 小荷包

## 六、技术细节

### 模型设计统一性

所有模板系统遵循相同的设计模式：

```python
class XxxTemplate(BaseModel):
    name = CharField()          # 模板名称
    description = TextField()   # 模板描述
    is_public = BooleanField()  # 是否公开
    is_official = BooleanField() # 是否官方
    version = CharField()       # 版本号
    update_notes = TextField()  # 更新说明
    owner = ForeignKey(User)    # 属主

class XxxTemplateItem(BaseModel):
    template = ForeignKey(XxxTemplate)
    # ... 具体字段根据模板类型而定
```

### 信号处理器

**account/signals.py**:
```python
@receiver(user_signed_up)
def apply_official_account_templates_on_signup(sender, request, user, **kwargs):
    apply_official_account_templates(user)
```

**maps/signals.py**:
```python
@receiver(user_signed_up)
def apply_official_templates_on_signup(sender, request, user, **kwargs):
    apply_official_templates(user)
```

**translate/signals.py**:
```python
@receiver(post_save, sender=User)
def create_user_config(sender, instance, created, **kwargs):
    if created:
        FormatConfig.get_user_config(user=instance)
```

### 应用模板逻辑

模板应用支持两种模式：

1. **merge（合并）** - 默认模式
   - 保留现有数据
   - 只添加新数据
   - 冲突时可选择跳过或覆盖

2. **overwrite（覆盖）**
   - 删除所有现有数据
   - 重新创建

## 七、使用示例

### 1. 管理员初始化系统

```bash
# 首次部署时初始化官方模板和 admin 用户
python manage.py init_official_templates

# 更新官方模板
python manage.py init_official_templates --force
```

### 2. 用户注册（自动初始化）

用户通过前端注册后，系统自动：
- 创建 85 个标准账户
- 创建 39 个常用映射
- 创建格式化配置

### 3. 匿名用户使用解析功能

匿名用户访问 `/api/translate/trans` 时：
- 使用 admin 用户的账户和映射数据
- 可以正常解析账单
- 无法保存或修改数据

### 4. 用户应用其他模板

```bash
# API 调用示例
POST /api/account-templates/{id}/apply/
{
    "action": "merge",
    "conflict_resolution": "skip"
}
```

## 八、注意事项

### 1. 模板依赖关系

- 映射模板依赖账户模板（映射项需要引用账户）
- 因此初始化顺序必须是：账户 → 映射 → 配置

### 2. 幂等性保证

所有初始化操作都是幂等的：
- 多次运行不会重复创建数据
- 使用 `get_or_create` 或冲突检查

### 3. 性能考虑

- 模板应用使用数据库事务（`@transaction.atomic`）
- 账户创建会自动创建父账户，避免手动维护层级关系

### 4. 数据隔离

- 每个用户的数据完全隔离
- 匿名用户只能读取 admin 用户数据
- 模板可以跨用户共享（公开模板）

## 九、扩展指南

### 添加新的官方映射

编辑 `init_official_templates.py`，在相应的 `*_mappings` 列表中添加：

```python
expense_mappings = [
    # ... 现有映射
    ('新商户关键字', '新商户名称', 'Expenses:对应账户', 'CNY'),
]
```

### 创建自定义模板类型

如需添加新的模板类型（如交易规则模板），遵循以下步骤：

1. 创建模板模型（参考 `AccountTemplate`）
2. 创建序列化器
3. 创建视图集（包含 apply 方法）
4. 注册路由和 Admin
5. 在信号处理器中添加自动应用逻辑

### 更新官方模板版本

1. 修改模板定义和版本号
2. 运行 `init_official_templates --force`
3. （可选）提供迁移脚本给现有用户

## 十、故障排查

### 问题：新用户没有获得初始数据

**检查项**:
1. 确认信号处理器已注册（`apps.py` 中的 `ready()` 方法）
2. 确认官方模板已创建（`Template.objects.filter(is_official=True)`）
3. 查看日志输出（`logger.info`）

### 问题：匿名用户无法访问数据

**检查项**:
1. 确认 admin（id=1）用户存在
2. 确认权限类配置正确（`AnonymousReadOnlyPermission`）
3. 确认过滤器配置正确（`AnonymousUserFilterBackend`）

### 问题：模板应用失败

**常见原因**:
1. 账户不存在 - 确保先应用账户模板
2. 权限不足 - 确保用户已登录
3. 数据冲突 - 使用合适的冲突解决策略

## 十一、API 使用示例

### 获取官方账户模板

```bash
GET /api/account-templates/?is_official=true

Response:
{
    "count": 1,
    "results": [
        {
            "id": 1,
            "name": "中国用户标准账户模板",
            "description": "适用于中国用户的标准 Beancount 账户结构",
            "is_official": true,
            "is_public": true,
            "version": "1.0.0",
            "items_count": 66
        }
    ]
}
```

### 应用账户模板

```bash
POST /api/account-templates/1/apply/
{
    "action": "merge",
    "conflict_resolution": "skip"
}

Response:
{
    "message": "账户模板应用成功",
    "result": {
        "created": 85,
        "skipped": 0,
        "overwritten": 0
    }
}
```

### 获取用户格式化配置

```bash
GET /api/config/

Response:
{
    "id": 1,
    "flag": "*",
    "show_note": true,
    "show_tag": true,
    "show_time": true,
    "show_uuid": true,
    "show_status": true,
    "show_discount": true,
    "income_template": "Income:Discount",
    "commission_template": "Expenses:Finance:Commission",
    "currency": "CNY",
    "ai_model": "BERT",
    "owner": 1
}
```

## 十二、维护建议

1. **定期审查官方模板** - 根据用户反馈更新常用映射
2. **版本化管理** - 每次重大更新增加版本号
3. **保持数据完整性** - 确保映射引用的账户存在
4. **监控自动化流程** - 定期检查新用户初始化日志
5. **备份模板数据** - 定期导出官方模板配置

## 十三、相关文件

### 模型文件
- `project/apps/account/models.py` - Account, AccountTemplate, AccountTemplateItem
- `project/apps/maps/models.py` - Expense, Assets, Income, Template, TemplateItem
- `project/apps/translate/models.py` - FormatConfig, ParseFile

### 信号处理器
- `project/apps/account/signals.py` - 账户模板自动应用
- `project/apps/maps/signals.py` - 映射模板自动应用
- `project/apps/translate/signals.py` - 格式化配置自动创建

### 管理命令
- `project/apps/account/management/commands/init_official_templates.py` - 官方模板初始化
- `project/apps/account/management/commands/init_accounts.py` - 账户初始化（已弃用）

### 视图集
- `project/apps/account/views.py` - AccountViewSet, AccountTemplateViewSet
- `project/apps/maps/views.py` - ExpenseViewSet, AssetsViewSet, IncomeViewSet, TemplateViewSet
- `project/apps/translate/views/views.py` - UserConfigAPI

### 序列化器
- `project/apps/account/serializers.py` - 账户和账户模板序列化器
- `project/apps/maps/serializers.py` - 映射和映射模板序列化器
- `project/apps/translate/serializers.py` - 格式化配置序列化器

