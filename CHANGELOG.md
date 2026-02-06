# Changelog

## [5.8.2](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.8.1...5.8.2) (2026-02-06)

### Bug Fixes

* balance ([#72](https://github.com/dhr2333/Beancount-Trans-Backend/issues/72)) ([4c5873e](https://github.com/dhr2333/Beancount-Trans-Backend/commit/4c5873eaf8a6a361f0c52ad693d2a3c636e5c5db))

## [5.8.1](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.8.0...5.8.1) (2026-02-06)

### Bug Fixes

* balance ([#71](https://github.com/dhr2333/Beancount-Trans-Backend/issues/71)) ([3d29e99](https://github.com/dhr2333/Beancount-Trans-Backend/commit/3d29e995e664de064f727b2108cef49a4ce1f0a4))

## [5.8.0](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.7.0...5.8.0) (2026-02-06)

### Features

* Add date field validation for transaction items in reconciliation ([#69](https://github.com/dhr2333/Beancount-Trans-Backend/issues/69)) ([b8669cf](https://github.com/dhr2333/Beancount-Trans-Backend/commit/b8669cf3c4940805e33a810a32b3378012075b93))

## [5.7.0](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.6.1...5.7.0) (2026-02-04)

### Features

* 文件解析支持审核功能 ([#67](https://github.com/dhr2333/Beancount-Trans-Backend/issues/67)) ([aba134a](https://github.com/dhr2333/Beancount-Trans-Backend/commit/aba134a2fd1a41fbcd017ef253e0b5e68b3299cb))

## [5.6.1](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.6.0...5.6.1) (2026-02-01)

### Bug Fixes

* 对账无差额时忽略 `transaction_items` 条目 ([#66](https://github.com/dhr2333/Beancount-Trans-Backend/issues/66)) ([78d3e84](https://github.com/dhr2333/Beancount-Trans-Backend/commit/78d3e847952026a48757d9a2e553639a0f050854))

## [5.6.0](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.5.1...5.6.0) (2026-01-30)

### Features

* Automatically generate reconciliation tasks when creating a new user. ([#64](https://github.com/dhr2333/Beancount-Trans-Backend/issues/64)) ([c6b9bc0](https://github.com/dhr2333/Beancount-Trans-Backend/commit/c6b9bc0b6a144c0b856e66757e8a2262a3d9b13b))

## [5.5.1](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.5.0...5.5.1) (2026-01-29)

### Bug Fixes

* Ensure proper handling of parent-child relationships during account deletion ([#63](https://github.com/dhr2333/Beancount-Trans-Backend/issues/63)) ([20420f3](https://github.com/dhr2333/Beancount-Trans-Backend/commit/20420f36638fc6fed2e95eb6fdc2b7f99eb32300))

## [5.5.0](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.4.4...5.5.0) (2026-01-28)

### Features

* Add user filtering and optimization in ScheduledTask admin ([#62](https://github.com/dhr2333/Beancount-Trans-Backend/issues/62)) ([e03a632](https://github.com/dhr2333/Beancount-Trans-Backend/commit/e03a632547f3e23efffc13ddaf8cb71cf44fe195))

## [5.4.4](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.4.3...5.4.4) (2026-01-28)

### Bug Fixes

* 实现账户对账周期与待办管理的闭环 ([#58](https://github.com/dhr2333/Beancount-Trans-Backend/issues/58)) ([a91848a](https://github.com/dhr2333/Beancount-Trans-Backend/commit/a91848a5a53195c3124aaa20879fdb2f9d7f39e2))

## [5.4.3](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.4.2...5.4.3) (2026-01-26)

### Bug Fixes

* Prevent self-referencing parent accounts in Account model ([#56](https://github.com/dhr2333/Beancount-Trans-Backend/issues/56)) ([f0768fe](https://github.com/dhr2333/Beancount-Trans-Backend/commit/f0768feb0e5d8c44678053c4d3ba01295dfeb978))

## [5.4.2](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.4.1...5.4.2) (2026-01-14)

### Bug Fixes

* Update Account model to use PROTECT for parent relationship and enhance validation ([#54](https://github.com/dhr2333/Beancount-Trans-Backend/issues/54)) ([6deccb7](https://github.com/dhr2333/Beancount-Trans-Backend/commit/6deccb782c0363cf69f89a87bf14c273d917f539))

## [5.4.1](https://github.com/dhr2333/Beancount-Trans-Backend/compare/5.4.0...5.4.1) (2026-01-13)

### Bug Fixes

* Fixed the issue where anonymous users could not access the formatted output page. ([#52](https://github.com/dhr2333/Beancount-Trans-Backend/issues/52)) ([0382dd4](https://github.com/dhr2333/Beancount-Trans-Backend/commit/0382dd4e4910b82d208017cc35df95911af0ca87))

## 1.0.0 (2025-11-12)

### Features

* enhance asset and income tag management in AccountHandler and ExpenseHandler ([f1bd262](https://github.com/dhr2333/Beancount-Trans-Backend/commit/f1bd262d0f60c6be3e974b2ee759ebf75a595b81))
* support anonymous user access to data using default user ID=1 ([#29](https://github.com/dhr2333/Beancount-Trans-Backend/issues/29)) ([24cc6cf](https://github.com/dhr2333/Beancount-Trans-Backend/commit/24cc6cfbb6919b5cf8133d0b213879718a7cef2c))
* Template management adds billing file example ([#37](https://github.com/dhr2333/Beancount-Trans-Backend/issues/37)) ([d1ba404](https://github.com/dhr2333/Beancount-Trans-Backend/commit/d1ba404722b6434fe675238d34059226c29bcef4))

### Bug Fixes

* add null checks for asset retrieval in various views and handlers to prevent errors ([4ba959f](https://github.com/dhr2333/Beancount-Trans-Backend/commit/4ba959f829cbe13f3d5ffc26fad0daeabb02ddfe))
* Fixed an issue where the transfer-out and transfer-in symbols would always be swapped when automatically transferring funds from Alipay's Yu'ebao account. ([#42](https://github.com/dhr2333/Beancount-Trans-Backend/issues/42)) ([eb49fa3](https://github.com/dhr2333/Beancount-Trans-Backend/commit/eb49fa323eaca6f515c82fbf4392210a075006ec))

本文件将由 semantic-release 自动维护，用于记录 Beancount-Trans-Backend 的版本变化。
