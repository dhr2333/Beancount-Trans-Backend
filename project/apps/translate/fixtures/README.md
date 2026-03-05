# 解析模块测试用 Fixtures

本目录为 **Django loaddata 格式** 的测试数据，用于测试时向数据库注入 User、Expense、Income、Assets 等表的数据。

- **格式**：`manage.py loaddata` 可加载的 JSON（含 `model`、`pk`、`fields`）。
- **用途**：仅用于**测试**（如解析、映射相关用例），**不参与**官方模板或 `init_official_templates`。
- **与官方模板的区别**：官方模板定义在 `project/fixtures/official_templates/`，用于初始化账户/映射模板；本目录是「已有数据」的快照，用于还原测试场景。

若测试已不再通过 loaddata 使用这些文件，可考虑移除或迁移到 `tests/fixtures/`。
