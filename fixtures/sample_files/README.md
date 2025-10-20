# 案例文件说明

## 文件用途

本目录包含用于新用户初始化的案例账单文件，帮助用户快速了解系统功能。

## 文件列表

- `完整测试_微信.csv` - 微信支付账单示例文件
- `完整测试_支付宝.csv` - 支付宝账单示例文件

## 使用方式

这些文件通过 `init_official_templates` 管理命令自动加载到 admin 用户，新用户注册时会自动获得这些文件的引用。

## 文件格式

- 格式：CSV
- 编码：UTF-8
- 内容类型：text/csv

## 维护说明

- 如需更新案例文件，请替换对应文件并重新运行初始化命令
- 文件内容应保持真实性和代表性，便于用户理解系统功能
- 文件大小应适中，避免影响系统性能

## 相关命令

```bash
# 初始化案例文件
python manage.py init_official_templates --force

# 仅重新创建案例文件（需要修改代码）
python manage.py init_official_templates --force
```
