# project/apps/translate/services/steps.py
from typing import Dict
from project.utils.file import BeanFileManager, convert_to_csv_bytes,convert_to_utf8, create_text_stream
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.apps.translate.services.pipeline import Step
from project.apps.translate.services.init.bill_init_factory import InitFactory
from project.apps.translate.services.parse.filters import TransactionFilter
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.translate.utils import *
from project.apps.translate.views.AliPay import *
from project.apps.translate.views.WeChat import *
from project.apps.translate.views.BOC_Debit import *
from project.apps.translate.views.CMB_Credit import *
from project.apps.translate.views.ICBC_Debit import *
from project.apps.translate.views.CCB_Debit import *
import logging
import os


logger = logging.getLogger(__name__)

class ConvertToCSVStep(Step):
    """对象转换步骤：将上传文件转换为CSV格式的文件对象"""
    def execute(self, context: Dict) -> Dict:
        uploaded_file = context['uploaded_file']
        password = context['args'].get("password")

        try:
            # 转换为CSV字节内容
            csv_bytes = convert_to_csv_bytes(uploaded_file, password)

            # 检测编码并转换为UTF-8
            utf8_csv_bytes = convert_to_utf8(csv_bytes)

            # 创建内存文件对象
            # csv_file_object = create_in_memory_file(uploaded_file.name, utf8_csv_bytes)
            csv_file_object = create_text_stream(uploaded_file.name, utf8_csv_bytes)

            # 存储到上下文
            context['csv_file_object'] = csv_file_object
            return context

        except (DecryptionError, UnsupportedFileTypeError) as e:
            return self._error(context, f"文件转换失败: {str(e)}")
        except Exception as e:
            return self._error(context, f"CSV转换步骤异常: {str(e)}")


class InitializeBillStep(Step):
    """账单初始化步骤（集成策略模式+工厂方法）"""
    def execute(self, context: Dict) -> Dict:
        # 获取文本流对象
        csv_file = context['csv_file_object']

        # 重置文件指针以确保从头开始读取
        csv_file.seek(0)

        # 读取第一行
        first_line = csv_file.readline().strip()
        year = first_line[:4]
        card_number = card_number_get_key(first_line)

        try:
            # 工厂方法创建策略
            strategy = InitFactory.create_strategy(first_line)

            # 策略执行初始化
            initialized_bill = strategy.init(csv_file, card_number=card_number, year=year)

            # 结果存入上下文
            context['initialized_bill'] = initialized_bill
            context['bill_type'] = initialized_bill[0]['bill_identifier']
            return context

        except ValueError as e:  # 无匹配策略
            return self._error(context, f"不支持的账单类型: {str(e)}")
        except Exception as e:  # 初始化异常
            return self._error(context, f"账单初始化异常: {str(e)}")


class PreFilterStep(Step):
    """预过滤步骤：基于原始数据的简单规则过滤"""
    def execute(self, context):
        bill_data = context['initialized_bill']
        args = context['args']
        bill_type = context['bill_type']
        # print(context['bill_type'])  # alipay
        try:
            filter = TransactionFilter(args, bill_type)
            # print(bill_data)  # [{'transaction_time': '2024-02-25 20:01:48', 'transaction_category': '母婴亲子', 'counterparty': '十月**店', 'commodity': '【天猫U先】十月结晶会员尊享精致妈咪出行必备生活随心包4件套 等多件', 'transaction_type': '/', 'amount': 14.8, 'payment_method': '亲情卡(凯义(王凯义))', 'transaction_status': '交易成功', 'notes': '/', 'bill_identifier': 'alipay', 'uuid': '2024022522001174561439593142', 'discount': False}]
            filter_data = filter.apply_pre_filters(bill_data)
            context['prefilter_bill'] = filter_data
            logger.info(f"预过滤后剩余记录数: {len(filter_data)}/{len(bill_data)}")
            return context
        except Exception as e:
            return self._error(context, f"预过滤步骤异常: {str(e)}")


class ParseStep(Step):
    """交易解析步骤：解析账单中的交易数据"""
    def execute(self,  context: Dict) -> Dict:
        import hashlib
        owner_id = context['owner_id']
        config = context['config']
        bill_data = context['prefilter_bill']

        try:
            for row in bill_data:
                # 解析单条交易记录
                parsed_entry = single_parse_transaction(row, owner_id, config, None)
                # 存入原始数据
                parsed_entry['_original_row'] = row
                # 生成缓存键
                if parsed_entry['uuid']:
                    cache_key = parsed_entry['uuid']
                else:
                    # 使用哈希值作为唯一标识符
                    row_str = str(row)
                    cache_key = hashlib.md5(row_str.encode()).hexdigest()
                parsed_entry['cache_key'] = cache_key

                # 添加解析结果到上下文
                if 'parsed_data' not in context:
                    context['parsed_data'] = []
                context['parsed_data'].append(parsed_entry)
        except Exception as e:
            import traceback
            logger.error(f"解析步骤详细错误: {traceback.format_exc()}")
            return self._error(context, f"解析步骤异常: {str(e)}")
        # logger.info(context['parsed_data'])
        return context


class PostFilterStep(Step):
    """后过滤步骤：基于解析后的结构化数据进行过滤"""
    def execute(self, context: Dict) -> Dict:
        parsed_data = context['parsed_data']
        args = context['args']
        bill_type = context['bill_type']
        try:
            filter = TransactionFilter(args, bill_type)
            # print(parsed_data)  # [{'date': '2024-02-25', 'time': '20:01:48', 'uuid': '2024022522001174561439593142', 'status': 'ALiPay - 交易成功', 'payee': '十月结晶', 'note': '【天猫U先】十月结晶会员尊享精致妈咪出行必备生活随心包4件套 等多件', 'tag': None, 'balance': None, 'balance_date': '2024-02-26', 'expense': 'Expenses:Shopping:Parent', 'expenditure_sign': '', 'account': 'Equity:OpenBalance', 'account_sign': '-', 'amount': '14.80', 'installment_granularity': 'MONTHLY', 'installment_cycle': 3, 'discount': False, 'currency': 'CNY', 'selected_expense_key': '十月结晶', 'expense_candidates_with_score': [{'key': '等多件', 'score': 0.5471}, {'key': '出行', 'score': 0.557}, {'key': '**', 'score': 0.5499}, {'key': '十月结晶', 'score': 0.5642}], 'actual_amount': '14.80', '_original_row': {'transaction_time': '2024-02-25 20:01:48', 'transaction_category': '母婴亲子', 'counterparty': '十月**店', 'commodity': '【天猫U先】十月结晶会员尊享精致妈咪出行必备生活随心包4件套 等多件', 'transaction_type': '/', 'amount': 14.8, 'payment_method': '亲情卡(凯义(王凯义))', 'transaction_status': '交易成功', 'notes': '/', 'bill_identifier': 'alipay', 'uuid': '2024022522001174561439593142', 'discount': False}, 'cache_key': '2024022522001174561439593142'}]
            filtered_data = filter.apply_post_filters(parsed_data)
            context['filtered_data'] = filtered_data
            logger.info(f"后过滤后剩余记录数: {len(filtered_data)}/{len(parsed_data)}")
            return context
        except Exception as e:
            return self._error(context, f"后过滤步骤异常: {str(e)}")


class CacheStep(Step):
    """结果缓存步骤：将处理结果缓存到数据库或其他存储中供重新解析步骤使用"""
    def execute(self,  context: Dict) -> Dict:
        from django.core.cache import cache


        parsed_data = context['parsed_data']
        args = context['args']
        for entry in parsed_data:
            cache_key = entry['cache_key']
            original_row = entry.pop('_original_row')
            cache_data = {
                "parsed_entry": entry,
                "original_row": original_row,
            }
            # 如果写入标志为False,则写入缓存
            if not args.get('write', True):
                cache.set(cache_key, cache_data, timeout=3600)
        return context


class FormatStep(Step):
    """交易格式化步骤：将交易数据格式化为.bean文本格式"""
    def execute(self,  context: Dict) -> Dict:
        parsed_data = context['filtered_data']
        args = context['args']
        config = context['config']
        if 'formatted_data' not in context:
            context['formatted_data'] = []
        for entry in parsed_data:
            if args['balance'] is True:
                formatted = FormatData.balance_instance(entry)
            else:
                formatted = FormatData.format_instance(entry,config=config)
            formatted_dict = {
                "formatted": formatted,
                "selected_expense_key": entry.get("selected_expense_key"),
                "expense_candidates_with_score": entry.get("expense_candidates_with_score", []),
                # "uuid": entry.get("uuid"),
                "id": entry.get("cache_key"),
            }
            context['formatted_data'].append(formatted_dict)
        return context


class FileWritingStep(Step):
    """文件写入步骤：将处理后的数据写入文件（可选）"""
    def execute(self,  context: Dict) -> Dict:
        if context['args']['write']:
            username = context['username']
            
            # 尝试从 context 获取 user 对象，如果没有则从 username 获取
            user = context.get('user')
            if not user:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    # 如果找不到用户，回退到使用 username
                    user = username
            
            formatted_data = "\n\n".join([entry['formatted'].rstrip() for entry in context['formatted_data']])

            original_filename = context['uploaded_file'].name
            bean_file_path = BeanFileManager.get_bean_file_path(user, original_filename)

            # 确保trans目录存在
            # BeanFileManager.ensure_trans_directory(user)

            # 写入文件到trans目录
            with open(bean_file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_data)

            # 注意：include语句的添加已在上传文件时完成，解析功能仅处理文件内容的写入

        return context