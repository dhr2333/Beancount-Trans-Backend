# Changelog

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
