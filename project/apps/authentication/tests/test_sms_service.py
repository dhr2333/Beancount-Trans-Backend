import pytest
from unittest.mock import patch, MagicMock
from project.apps.authentication.sms import AliyunSMSService


class TestSMSService:
    """短信服务测试"""
    
    # def test_mock_mode(self):
    #     """测试模拟模式"""
    #     # 不配置阿里云参数，应该启用模拟模式
    #     sms_service = AliyunSMSService()
    #     assert sms_service.mock_mode is True
        
    #     # 发送验证码应该成功
    #     result = sms_service.send_code('13800138000', '123456')
    #     assert result is True
    
    # def test_phone_number_format(self):
    #     """测试手机号格式处理"""
    #     sms_service = AliyunSMSService()
        
    #     # 测试 +86 前缀
    #     result = sms_service.send_code('+8613800138000', '123456')
    #     assert result is True
        
    #     # 测试无前缀
    #     result = sms_service.send_code('13800138000', '123456')
    #     assert result is True
    
    def test_unsupported_international_number(self):
        """测试不支持的国际手机号"""
        sms_service = AliyunSMSService()
        
        # 测试非中国手机号
        result = sms_service.send_code('+12345678900', '123456')
        assert result is False
    
    @patch('project.apps.authentication.sms.AcsClient')
    def test_real_mode_success(self, mock_acs_client):
        """测试真实模式发送成功"""
        # 模拟配置
        with patch('project.apps.authentication.sms.settings') as mock_settings:
            mock_settings.ALIYUN_SMS_ACCESS_KEY_ID = 'test_key_id'
            mock_settings.ALIYUN_SMS_ACCESS_KEY_SECRET = 'test_key_secret'
            mock_settings.ALIYUN_SMS_SIGN_NAME = 'test_sign'
            mock_settings.ALIYUN_SMS_TEMPLATE_CODE = 'SMS_123456'
            
            # 模拟返回成功响应
            mock_client_instance = MagicMock()
            mock_client_instance.do_action_with_exception.return_value = b'{"Code":"OK"}'
            mock_acs_client.return_value = mock_client_instance
            
            sms_service = AliyunSMSService()
            sms_service.mock_mode = False
            sms_service.client = mock_client_instance
            
            result = sms_service.send_code('13800138000', '123456')
            assert result is True
    
    @patch('project.apps.authentication.sms.AcsClient')
    def test_real_mode_failure(self, mock_acs_client):
        """测试真实模式发送失败"""
        with patch('project.apps.authentication.sms.settings') as mock_settings:
            mock_settings.ALIYUN_SMS_ACCESS_KEY_ID = 'test_key_id'
            mock_settings.ALIYUN_SMS_ACCESS_KEY_SECRET = 'test_key_secret'
            mock_settings.ALIYUN_SMS_SIGN_NAME = 'test_sign'
            mock_settings.ALIYUN_SMS_TEMPLATE_CODE = 'SMS_123456'
            
            # 模拟返回失败响应
            mock_client_instance = MagicMock()
            mock_client_instance.do_action_with_exception.return_value = b'{"Code":"Error","Message":"Send failed"}'
            mock_acs_client.return_value = mock_client_instance
            
            sms_service = AliyunSMSService()
            sms_service.mock_mode = False
            sms_service.client = mock_client_instance
            
            result = sms_service.send_code('13800138000', '123456')
            assert result is False
    
    # def test_send_notification(self):
    #     """测试发送通知短信"""
    #     sms_service = AliyunSMSService()
        
    #     result = sms_service.send_notification(
    #         '13800138000',
    #         'SMS_NOTIFY_123',
    #         {'name': 'Test User', 'message': 'Hello'}
    #     )
    #     assert result is True

