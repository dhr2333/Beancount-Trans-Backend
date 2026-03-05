# 官方模板 JSON 数据

本目录为官方账户模板与映射模板的**唯一数据源**。运行 `init_official_templates` 时仅从此处加载；若任一文件缺失或校验失败，命令将报错并中止。

## 文件说明

| 文件 | 用途 |
|------|------|
| `account.json` | 官方账户模板（Beancount 账户结构） |
| `mapping_expense.json` | 官方支出映射模板 |
| `mapping_income.json` | 官方收入映射模板 |
| `mapping_assets.json` | 官方资产映射模板 |

## 结构说明

### account.json

- 顶层：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项为 `account_path`（必填）、`enable`（可选，默认 true）、`reconciliation_cycle_unit` / `reconciliation_cycle_interval`（可选，需成对）

### mapping_expense.json

- 顶层：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项为 `key`（必填）、`payee`、`account`、`currency`（可选）

### mapping_income.json

- 顶层：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项为 `key`（必填）、`account`（必填）、`payer`（可选）

### mapping_assets.json

- 顶层：`name`, `description`, `version`, `update_notes`
- `items`: 数组，每项为 `key`、`full`、`account`（均必填）

## 更新后生效

修改任意 JSON 后，执行以下命令使数据库中的官方模板与文件一致（会按 `--force` 重建官方模板）：

```bash
pipenv run python manage.py init_official_templates --force
```

数据由维护者自行填充与维护。
