import json
import logging
from django.conf import settings
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

logger = logging.getLogger(__name__)


class AliyunSMSService:
    """阿里云短信服务"""
    
    def __init__(self):
        self.access_key_id = getattr(settings, 'ALIYUN_SMS_ACCESS_KEY_ID', '')
        self.access_key_secret = getattr(settings, 'ALIYUN_SMS_ACCESS_KEY_SECRET', '')
        self.sign_name = getattr(settings, 'ALIYUN_SMS_SIGN_NAME', '')
        self.template_code = getattr(settings, 'ALIYUN_SMS_TEMPLATE_CODE', '')
        
        # 检查配置
        if not all([self.access_key_id, self.access_key_secret, self.sign_name, self.template_code]):
            logger.warning("阿里云短信服务配置不完整，将使用模拟模式")
            self.mock_mode = True
        else:
            self.mock_mode = False
            self.client = AcsClient(self.access_key_id, self.access_key_secret, 'cn-hangzhou')
    
    def send_code(self, phone_number, code):
        """
        发送验证码短信
        
        Args:
            phone_number: 手机号（E164格式，如+8613800138000）
            code: 验证码
            
        Returns:
            bool: 发送是否成功
        """
        # 去掉手机号的 + 和国家代码（假设是中国手机号）
        if phone_number.startswith('+86'):
            phone_number = phone_number[3:]
        elif phone_number.startswith('+'):
            logger.error(f"不支持的国际手机号: {phone_number}")
            return False
        
        # 模拟模式（开发/测试环境）
        if self.mock_mode:
            logger.info(f"[模拟模式] 发送验证码到 {phone_number}: {code}")
            return True
        
        try:
            # 构建请求
            request = CommonRequest()
            request.set_accept_format('json')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_method('POST')
            request.set_protocol_type('https')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')
            
            # 设置参数
            request.add_query_param('PhoneNumbers', phone_number)
            request.add_query_param('SignName', self.sign_name)
            request.add_query_param('TemplateCode', self.template_code)
            request.add_query_param('TemplateParam', json.dumps({'code': code}))
            
            # 发送请求
            response = self.client.do_action_with_exception(request)
            response_data = json.loads(response)
            
            # 检查返回结果
            if response_data.get('Code') == 'OK':
                logger.info(f"短信发送成功: {phone_number}")
                return True
            else:
                logger.error(f"短信发送失败: {response_data.get('Message', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"短信发送异常: {str(e)}")
            return False
    
    def send_notification(self, phone_number, template_code, template_params):
        """
        发送通知短信
        
        Args:
            phone_number: 手机号
            template_code: 短信模板代码
            template_params: 模板参数字典
            
        Returns:
            bool: 发送是否成功
        """
        # 去掉手机号的 + 和国家代码
        if phone_number.startswith('+86'):
            phone_number = phone_number[3:]
        elif phone_number.startswith('+'):
            logger.error(f"不支持的国际手机号: {phone_number}")
            return False
        
        if self.mock_mode:
            logger.info(f"[模拟模式] 发送通知到 {phone_number}, 模板: {template_code}, 参数: {template_params}")
            return True
        
        try:
            request = CommonRequest()
            request.set_accept_format('json')
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_method('POST')
            request.set_protocol_type('https')
            request.set_version('2017-05-25')
            request.set_action_name('SendSms')
            
            request.add_query_param('PhoneNumbers', phone_number)
            request.add_query_param('SignName', self.sign_name)
            request.add_query_param('TemplateCode', template_code)
            request.add_query_param('TemplateParam', json.dumps(template_params))
            
            response = self.client.do_action_with_exception(request)
            response_data = json.loads(response)
            
            if response_data.get('Code') == 'OK':
                logger.info(f"通知短信发送成功: {phone_number}")
                return True
            else:
                logger.error(f"通知短信发送失败: {response_data.get('Message', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"通知短信发送异常: {str(e)}")
            return False

