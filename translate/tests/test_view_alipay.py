# tests/test_alipay_views.py
import csv
from io import StringIO
from django.test import TestCase
from django.contrib.auth.models import User
from translate.models import Assets
from translate.views.AliPay import (  # 替换为实际导入路径
    AliPayInitStrategy,
    alipay_ignore,
    BILL_ALI,
)

class AliPayProcessorTest(TestCase):
    def setUp(self):
        # 创建测试用户和资产
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.key_list = ['icbc', 'cmb']
        
        # 创建测试资产账户
        Assets.objects.create(
            key='icbc',
            full='工商银行(6222)',
            assets='Assets:Bank:ICBC',
            owner=self.user
        )
        Assets.objects.create(
            key='cmb',
            full='招商银行信用卡(3788)',
            assets='Liabilities:CreditCard:CMB',
            owner=self.user
        )

    def _create_test_csv(self, rows):
        """生成测试CSV文件流"""
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        for row in rows:
            writer.writerow(row)
        csv_data.seek(0)
        return csv_data

    # # 测试初始化策略
    # def test_init_strategy_skip_rows(self):
    #     """测试跳过前24行"""
    #     rows = [['Header']*12]*30  # 生成30行测试数据
    #     csv_data = self._create_test_csv(rows)
        
    #     strategy = AliPayInitStrategy()
    #     result = strategy.init(csv.reader(csv_data))
    #     self.assertEqual(len(result), 6)  # 30-24=6

    # def test_record_normalization(self):
    #     """测试交易记录标准化"""
    #     test_row = [
    #         '2024-01-01 17:43:08','信用借还','华夏银行（解析文件中未包含华夏信用卡）','/','信用卡还款','不计收支','301.00','余额宝','还款成功','2022062100003001560037233415'	,''	,'',
    #     ]
    #     csv_data = self._create_test_csv([test_row]*25)  # 前24行被跳过
        
    #     strategy = AliPayInitStrategy()
    #     records = strategy.init(csv.reader(csv_data))
        
    #     self.assertEqual(records[0]['amount'], '301.00')
    #     self.assertEqual(records[0]['payment_method'], '余额宝')
    #     self.assertEqual(records[0]['bill_identifier'], BILL_ALI)

    # 测试过滤规则
    def test_ignore_rules(self):
        """测试交易忽略逻辑"""
        test_data = [
            {'bill_identifier': BILL_ALI, 'transaction_status': '退款成功'},
            {'bill_identifier': BILL_ALI,  'transaction_status': '支付成功', 'commodity': '余额宝-2022.10.12-收益发放'},
            {'bill_identifier': 'OTHER', 'transaction_status': '支付成功'}
        ]
        
        results = [alipay_ignore(None, d) for d in test_data]
        self.assertEqual(results, [True, True, False])
