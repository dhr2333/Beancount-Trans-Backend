# project/apps/translate/services/parsing/steps.py
from typing import Dict
from .pipeline import Step
from project.utils.file import  convert_to_csv_bytes,convert_to_utf8, create_text_stream
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from translate.services.init.bill_init_factory import InitFactory
from translate.services.parse.filters import TransactionFilter
from translate.services.parse.transaction_parser import single_parse_transaction
from translate.utils import *
from translate.views.AliPay import *
from translate.views.WeChat import *
from translate.views.BOC_Debit import *
from translate.views.CMB_Credit import *
from translate.views.ICBC_Debit import *
from translate.views.CCB_Debit import *


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
            # print(csv_file_object)
  
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
        try:
            # 工厂方法创建策略
            strategy = InitFactory.create_strategy(first_line)
            
            # 策略执行初始化
            initialized_bill = strategy.init(csv_file)

            # 结果存入上下文
            context['initialized_bill'] = initialized_bill
            # context['bill_type'] = strategy.__class__.__name__
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
        try:
            filter = TransactionFilter(args)
            filter_data = filter.apply_bill_filters(bill_data)
            context['prefilter_bill'] = filter_data
            # logger.info(f"过滤后剩余记录数: {len(filter_data)}/{len(bill_data)}")
            return context
        except Exception as e:
            return self._error(context, f"预过滤步骤异常: {str(e)}")


class ParseStep(Step):
    """交易解析步骤：解析账单中的交易数据"""
    def execute(self,  context: Dict) -> Dict:
        print("Parsing transaction data...")
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
            return self._error(context, f"解析步骤异常: {str(e)}")
        # logger.info(context['parsed_data'])
        return context


class PostFilterStep(Step):
    """后过滤步骤：基于解析后的结构化数据进行过滤"""
    def execute(self, context: Dict) -> Dict:
        print("Post-filtering parsed transaction data...")
        parsed_data = context['parsed_data']
        args = context['args']
        try:
            filter = TransactionFilter(args)
            filtered_data = filter.apply_entry_filters(parsed_data)
            context['filtered_data'] = filtered_data
            # logger.info(f"后过滤后剩余记录数: {len(filtered_data)}/{len(parsed_data)}")
            return context
        except Exception as e:
            return self._error(context, f"后过滤步骤异常: {str(e)}")


class CacheStep(Step):
    """结果缓存步骤：将处理结果缓存到数据库或其他存储中供重新解析步骤使用"""
    def execute(self,  context: Dict) -> Dict:
        print("Caching processed results for future use...")
        from django.core.cache import cache


        parsed_data = context['parsed_data']
        for entry in parsed_data:
            cache_key = entry['cache_key']
            original_row = entry.pop('_original_row')
            cache_data = {
                "parsed_entry": entry,
                "original_row": original_row,
            }
            # print(cache_data)
            cache.set(cache_key, cache_data, timeout=3600)
        return context


class FormatStep(Step):
    """交易格式化步骤：将交易数据格式化为.bean文本格式"""
    def execute(self,  context: Dict) -> Dict:
        print("Formatting transaction data into .bean text format...")
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
                "uuid": entry.get("uuid"),
            }
            context['formatted_data'].append(formatted_dict)
        return context


class FileWritingStep(Step):
    """文件写入步骤：将处理后的数据写入文件（可选）"""
    def execute(self,  context: Dict) -> Dict:
        print("Writing processed data to file...")
        return context
