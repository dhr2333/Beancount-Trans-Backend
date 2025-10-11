# 模板系统更新日志

## 版本 1.0.0 (2025-10-10)

### 新增功能

#### 1. 账户模板系统

- **新增模型**: `AccountTemplate` 和 `AccountTemplateItem`
- **功能**: 管理 Beancount 账户结构模板
- **特性**:
  - 支持官方/公开/私有模板
  - 支持版本管理和更新说明
  - 新用户注册时自动应用官方模板

- **API 端点**:
  - `GET/POST /api/account-templates/` - 列表和创建
  - `GET/PUT/DELETE /api/account-templates/{id}/` - 详情、更新和删除
  - `POST /api/account-templates/{id}/apply/` - 应用模板

- **Admin 管理**: 可在后台管理账户模板

#### 2. 统一初始化管理命令

- **命令**: `python manage.py init_official_templates`
- **功能**: 一键初始化官方模板和默认用户
- **参数**:
  - `--force` - 强制重建模板
  - `--skip-admin` - 跳过创建 admin 用户

- **执行内容**:
  1. 创建/验证 admin 用户（id=1）
  2. 创建官方账户模板（66 个标准账户）
  3. 创建官方映射模板（支出30项、资产7项、收入2项）
  4. 为 admin 用户应用所有模板
  5. 创建格式化配置

#### 3. 完整的映射模板数据

- **官方支出映射**: 30 个常用商户
  - 饮品店: 蜜雪冰城、古茗、喜茶、茶百道等
  - 餐饮店: 肯德基、华莱士、塔斯汀等
  - 平台: 淘宝、京东、拼多多、美团、饿了么等

- **官方资产映射**: 7 个常用支付方式
  - 支付宝: 余额、余额宝、花呗
  - 微信: 零钱、零钱通

- **官方收入映射**: 2 个常用收入类型
  - 红包、小荷包

#### 4. 信号处理优化

- **account/signals.py**: 监听 `user_signed_up`，自动应用账户模板
- **maps/signals.py**: 监听 `user_signed_up`，自动应用映射模板
- **translate/signals.py**: 监听 `post_save(User)`，自动创建格式化配置

#### 5. 文档完善

新增文档：
- `docs/TEMPLATE_SYSTEM.md` - 模板系统架构详解
- `docs/QUICK_START.md` - 快速开始指南
- `docs/DEPLOYMENT_CHECKLIST.md` - 部署检查清单
- `docs/CHANGELOG_TEMPLATE_SYSTEM.md` - 本更新日志

更新文档：
- `README.md` - 添加快速开始和核心特性说明

#### 6. 工具脚本

- `check_system_status.py` - 系统状态快速检查

### 改进

- **统一架构**: 三个模板系统（账户、映射、配置）遵循统一的设计模式
- **开箱即用**: 新用户无需手动配置，注册即可使用
- **匿名试用**: 匿名用户可以试用全部功能（只读）
- **可维护性**: 官方模板集中管理，易于更新和维护

### 数据迁移

- **account_config.0005**: 创建账户模板表
- 向后兼容，不影响现有数据

### Breaking Changes

无破坏性变更。所有更改都是向后兼容的。

### 数据要求

系统正常运行需要：
1. admin 用户（id=1）存在
2. 官方模板已创建
3. admin 用户已应用官方模板

**自动满足**: 运行 `init_official_templates` 命令后自动满足所有要求

### 性能影响

- **新用户注册**: 增加约 1-2 秒（自动应用模板）
- **数据库**: 新增约 100 条记录（账户 + 映射）
- **存储**: 可忽略不计

### 测试

- ✓ 账户模板创建和应用
- ✓ 映射模板创建和应用
- ✓ 新用户自动初始化
- ✓ 匿名用户数据访问
- ✓ 账单解析功能
- ✓ 系统完整性验证

### 已知问题

无

### 后续计划

- [ ] 创建更多行业/地区特定的官方模板
- [ ] 添加模板导入/导出功能
- [ ] 支持模板版本迁移
- [ ] 添加模板推荐系统（根据用户行为）

### 参考

- 模板系统架构: [TEMPLATE_SYSTEM.md](TEMPLATE_SYSTEM.md)
- 快速开始: [QUICK_START.md](QUICK_START.md)
- 部署检查: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

