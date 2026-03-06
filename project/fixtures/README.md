# Fixtures 数据维护指南

本目录包含系统初始化所需的所有数据文件，包括官方模板和案例文件。这些文件是 `init_official_templates` 管理命令的**唯一数据源**。

## 目录结构

```
project/fixtures/
├── official_templates/     # 官方模板 JSON 数据
│   ├── account.json        # 账户模板
│   ├── mapping_expense.json # 支出映射模板
│   ├── mapping_income.json  # 收入映射模板
│   └── mapping_assets.json  # 资产映射模板
└── sample_files/            # 案例账单文件
    ├── 完整测试_微信.csv
    └── 完整测试_支付宝.csv
```

## 官方模板 (official_templates/)

### 文件说明

| 文件 | 用途 |
|------|------|
| `account.json` | 官方账户模板（Beancount 账户结构） |
| `mapping_expense.json` | 官方支出映射模板 |
| `mapping_income.json` | 官方收入映射模板 |
| `mapping_assets.json` | 官方资产映射模板 |

### 数据结构

#### account.json

- 顶层字段：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项包含：
  - `account_path`（必填）- 账户路径
  - `enable`（可选，默认 true）- 是否启用
  - `reconciliation_cycle_unit` / `reconciliation_cycle_interval`（可选，需成对）- 对账周期配置
  - `description`（可选）- 账户描述

#### mapping_expense.json

- 顶层字段：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项包含：
  - `key`（必填）- 匹配关键词
  - `payee`（可选）- 收款方（已隐藏隐私信息）
  - `account`（必填）- 账户路径
  - `currency`（可选）- 货币类型

#### mapping_income.json

- 顶层字段：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项包含：
  - `key`（必填）- 匹配关键词
  - `account`（必填）- 账户路径
  - `payer`（可选）- 付款方（已隐藏隐私信息，为 null）

#### mapping_assets.json

- 顶层字段：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项包含：
  - `key`（必填）- 匹配关键词
  - `full`（必填）- 完整描述
  - `account`（必填）- 账户路径

### 维护说明

1. **数据源唯一性**：这些 JSON 文件是官方模板的唯一数据源，运行 `init_official_templates` 时仅从此处加载
2. **数据校验**：若任一文件缺失或校验失败，命令将报错并中止
3. **隐私信息**：映射模板中的 `payee` 和 `payer` 字段已清空，避免泄露个人信息
4. **更新流程**：修改任意 JSON 后，执行以下命令使数据库中的官方模板与文件一致：

```bash
pipenv run python manage.py init_official_templates --force
```

## 案例文件 (sample_files/)

### 文件说明

- `完整测试_微信.csv` - 微信支付账单示例文件
- `完整测试_支付宝.csv` - 支付宝账单示例文件

### 文件格式

- 格式：CSV
- 编码：UTF-8
- 内容类型：text/csv

### 维护说明

1. **用途**：用于新用户初始化的案例账单文件，帮助用户快速了解系统功能
2. **加载方式**：通过 `init_official_templates` 管理命令自动加载到 admin 用户
3. **案例文件默认强制初始化**：每次执行 `init_official_templates` 时，案例文件都会按当前 fixtures 强制覆盖（与是否使用 `--force` 无关）。若 admin 已有案例文件，会先按「删除文件」语义清理：从 trans/main.bean 移除 include、删除对应 .bean 文件；若无其他用户引用同一 OSS 对象则一并删除 OSS 文件；再删除数据库记录；最后按 fixtures 重新上传并建记录。
4. **新用户**：新用户注册时会自动获得这些文件的引用（同一 OSS 对象，不重复上传）
5. **更新流程**：更新案例文件时，替换 `sample_files/` 下对应文件后，直接重新运行初始化即可（无需 `--force`）：

```bash
pipenv run python manage.py init_official_templates
```

6. **内容要求**：
   - 文件内容应保持真实性和代表性，便于用户理解系统功能
   - 文件大小应适中，避免影响系统性能

## 完整初始化流程

**首次部署或仅更新案例文件**（案例文件每次都会按 fixtures 覆盖）：

```bash
pipenv run python manage.py init_official_templates
```

**已修改官方模板 JSON、需要强制重建账户/映射模板时**：

```bash
pipenv run python manage.py init_official_templates --force
```

此命令会：

1. 创建或更新 admin 用户（id=1）
2. 加载官方账户模板（存在且无 `--force` 时跳过）
3. 应用账户模板到 admin 用户
4. 加载官方映射模板（存在且无 `--force` 时跳过）
5. 应用映射模板到 admin 用户
6. 创建格式化配置
7. **始终**按 fixtures 重建 admin 的案例文件（删除旧文件时无引用则同步删除 OSS 对象）

## 注意事项

- **数据一致性**：确保 JSON 文件格式正确，否则初始化会失败
- **版本控制**：建议在更新模板时更新 `version` 字段，并在 `update_notes` 中记录变更内容
- **备份**：更新前建议备份现有文件，避免数据丢失
- **测试**：更新后应在测试环境验证，确认无误后再部署到生产环境
