# Beancount-Trans-Backend

Beancount-Trans-Backend 是 Beancount-Trans 项目的后端子模块，用于处理与前端交互的数据和业务逻辑。

## 项目简介

Beancount-Trans-Backend 提供了与前端交互的 API 服务，处理用户请求及数据处理逻辑。本项目使用了 [Django](https://www.django-rest-framework.org/) 和 [Django Rest Framework](https://www.django-rest-framework.org/)（DRF）作为 Web 框架，并集成了多种扩展功能。

## 项目结构

```shell
Beancount-Trans-Backend/  # 项目根目录
├── bin  # 脚本目录（存放启动、备份脚本）
├── conf  # 配置文件，如uwsgi.ini
├── docs  # 文档统一存放
├── fixtures  # 数据库脚本
├── logs  # 日志文件
├── manage.py
├── project  # Django项目目录
│   ├── apps  # 若有新增功能，请在该目录下添加目录实现
│   │   ├── account  # 账户管理
│   │   │   ├── migrations
│   │   ├── maps  # 映射管理
│   │   │   ├── migrations
│   │   ├── owntracks  # Owntrack轨迹记录功能
│   │   │   ├── migrations
│   │   └── users  # 用户管理
│   │       ├── migrations
│   └── utils  # 通用工具
├── static  # 静态文件配置
├── templates  # 模板文件
│   ├── owntracks
│   └── translate
├── pyproject.toml  # pytest自动化测试配置文件
└── translate  # 转换功能目录，对转换功能进行二次开发只要关注该目录
    ├── migrations
    ├── tests.py
    └── views
        ├── AAA_Template.py  # 提供模板文件，适用于储蓄卡和信用卡
        ├── ABC_Debit.py
        ├── AliPay.py  # 支付宝账单
        ├── BOC_Debit.py
        ├── CCB_Debit.py
        ├── CEB_Debit.py
        ├── CITIC_Credit.py
        ├── CMB_Credit.py
        ├── CMB_Debit.py
        ├── HXB_Debit.py
        ├── ICBC_Debit.py
        ├── ICBC_Enterprise.py
        ├── NBCB_Debit.py
        ├── view.py  # 实现对转换功能的全流程，需要重点了解。
        ├── WeChat.py
        └── ZJRCUB_Debit.py
```

## API 文档

本项目提供了详细的 [API文档](https://trans.dhr2333.cn/api/redoc)，涵盖了所有的请求和响应格式、示例代码等内容。我们使用了 Django REST framework 中的 [API文档生成工具](https://www.django-rest-framework.org/topics/documenting-your-api/#third-party-packages-for-openapi-support) 来自动生成这些文档，确保其准确性和全面性。

### 测试

我们使用 `pytest` 进行测试，运行所有测试：

```shell
Beancount-Trans[dhr2333@ironstamp Beancount-Trans]$ pytest
================================================================================================================= test session starts =================================================================================================================
platform linux -- Python 3.12.3, pytest-8.2.2, pluggy-1.5.0
rootdir: /home/dhr2333/Desktop/GitHub/Beancount-Trans
configfile: pyproject.toml
testpaths: Beancount-Trans-Backend/translate
plugins: django-4.8.0
collected 0 items

================================================================================================================ no tests ran in 0.01s ================================================================================================================
```

## 贡献指南

如果你希望对该项目做出贡献，我们欢迎各种形式的贡献，包括报告 Bug、提建议、提交代码、改进文档等。

### 如何开始

- 了解项目: 仔细阅读项目的 README 文件和现有文档。
- 沟通: 加入我们的讨论平台（如 Slack、Discord、邮件列表等），提出问题或想法。

### 提交 Bug 报告

- 搜索现有问题: 在提交新问题前，先搜索一下是否已有相关问题。
- 创建新问题: 提供详细的描述，包括重现步骤、预期行为、实际行为、截图等。

### 提交功能请求

- 描述需求: 说明功能的用例和预期效果，最好能提供一些实际例子。
- 讨论: 在提交功能请求前，可以在讨论平台上先与维护者讨论，以确定是否符合项目的方向。

### 贡献代码

- Fork 仓库: 创建项目的副本到你的 GitHub 账户中。
- 克隆仓库: 将项目克隆到本地计算机。
- 创建分支: 为你的工作创建一个新的分支，例如 `feature/new-feature` 或 `bugfix/issue-123`。
- 进行更改: 在本地开发环境中进行更改并测试。
- 提交更改: 确保符合代码风格，提交你的更改并推送到你的 Fork 仓库。
- 创建 Pull Request: 在 GitHub 上创建一个 Pull Request，描述你的更改并关联相关的 Issue（如果有）。

### 文档贡献

- 改进现有文档: 修正拼写和语法错误，添加新的示例或解释。
- 创建新文档: 为新功能或模块编写说明文档。

### 参与测试

- 编写测试: 为你添加的新功能或修复编写单元测试或集成测试。
- 运行测试: 确保所有测试通过，并且不会引入新的 Bug。

### 反馈

如果你有任何疑问或建议，欢迎随时联系我们！

## 许可证

该项目的许可证信息，请查看 [LICENSE](https://github.com/dhr2333/Beancount-Trans-Backend/blob/main/LICENSE.txt)。
