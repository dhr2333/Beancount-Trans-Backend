# Changelog

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
