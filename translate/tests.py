from django.test import TestCase
from translate.views.view import format


class FormatTestCase(TestCase):
    def setUp(self):
        """
        初始化测试环境，你可以在这里初始化一些测试数据
        """
        self.data = ['2024-01-01 14:08:52', '信用借还', '中信银行', '信用卡还款', '/', '4.10', '余额宝', '还款成功', '', 'alipay', '2022100900003001860044469909']
        self.owner_id = 1

    def test_format(self):
        """
        测试 format 函数
        """
        result = format(self.data, self.owner_id)
        self.assertEqual(result['date'], "2024-01-01")
        self.assertEqual(result['time'], "14:08:52")
        self.assertEqual(result['uuid'], "2022100900003001860044469909")
        self.assertEqual(result['status'], "ALiPay - 还款成功")
        self.assertEqual(result['amount'], "4.10 CNY")
        self.assertEqual(result['payee'], "中信银行")
        self.assertEqual(result['notes'], "信用卡还款")
        self.assertEqual(result['expend_sign'], "")
        self.assertEqual(result['account_sign'], "-")
        self.assertEqual(result['expend'], "Unknown-Expend")
        self.assertEqual(result['account'], "Unknown-Account")
