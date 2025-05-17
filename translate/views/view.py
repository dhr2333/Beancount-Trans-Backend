import csv
import os
import datetime
import spacy
import torch
import logging

from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import timedelta
from datetime import datetime
from transformers import BertTokenizer, BertModel
from openai import OpenAI

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth import get_user_model
from mydemo.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from mydemo.utils.file import create_temporary_file, file_convert_to_csv, write_entry_to_file, read_and_write
from mydemo.utils.token import get_token_user_id
from mydemo.utils.tools import get_user_config
from translate.models import Expense, Income
from translate.utils import *
from translate.views.AliPay import *
from translate.views.WeChat import *
from translate.views.BOC_Debit import *
from translate.views.CMB_Credit import *
from translate.views.ICBC_Debit import *
from translate.views.CCB_Debit import *


User = get_user_model()
logger = logging.getLogger(__name__)

class AnalyzeView(View):
    def post(self, request):
        args = {key: request.POST.get(key) for key in request.POST}
        owner_id = get_token_user_id(request)  # 根据前端传入的JWT Token获取owner_id,如果是非认证用户或者Token过期则返回1(默认用户)
        config = get_user_config(User.objects.get(id=owner_id))
        uploaded_file = request.FILES.get('trans', None)  # 获取前端传入的文件

        if not uploaded_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        try:
            csv_file = file_convert_to_csv(uploaded_file, args["password"])  # 对文件格式进行判断并转换
            temp, encoding = create_temporary_file(csv_file)  # 创建临时文件并获取文件编码
        except DecryptionError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except UnsupportedFileTypeError as e:
            return JsonResponse({'error': str(e)}, status=415)

        if args['isCSVOnly'] == "true":
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="converted.csv"'

            with open(temp.name, newline='', encoding=encoding) as csvfile:
                read_and_write(csvfile,response)
            # 关闭并删除临时文件
            os.unlink(temp.name)
            return response

        try:
            with open(temp.name, newline='', encoding=encoding, errors="ignore") as csvfile:
                list = get_initials_bill(bill=csv.reader(csvfile))
            format_list = beancount_outfile(list, owner_id, args, config)
        except UnsupportedFileTypeError as e:
            return JsonResponse({'error': str(e)}, status=415)
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        finally:
            if 'temp' in locals():
                os.unlink(temp.name)

        return JsonResponse(format_list, safe=False, content_type='application/json')

    def get(self, request):
        return render(request, "translate/trans.html", {"title": "trans"})


def get_initials_bill(bill):
    first_line = next(bill)[0]
    year = first_line[:4]
    card_number = card_number_get_key(first_line)

    strategies = [
        (alipay_csvfile_identifier, AliPayInitStrategy()),
        (wechat_csvfile_identifier, WeChatInitStrategy()),
        (cmb_credit_csvfile_identifier, CmbCreditInitStrategy()),
        (boc_debit_csvfile_identifier, BocDebitInitStrategy()),
        (icbc_debit_csvfile_identifier, IcbcDebitInitStrategy()),
        (ccb_debit_csvfile_identifier, CcbDebitInitStrategy()),
    ]

    for identifier, parser_function in strategies:
        if isinstance(first_line, str) and identifier in first_line:
            return parser_function.init(bill, card_number=card_number, year=year)

    raise UnsupportedFileTypeError("当前账单不支持")


def should_ignore_row(row, ignore_data, args):
    return (ignore_data.wechatpay_ignore(row)
            or ignore_data.alipay_ignore(row)
            or ignore_data.alipay_fund_ignore(row)
            or ignore_data.cmb_credit_ignore(row, args.get("cmb_credit_ignore"))
            or ignore_data.boc_debit_ignore(row, args.get("boc_debit_ignore"))
            )


def beancount_outfile(data, owner_id: int, args, config):
    ignore_data = IgnoreData(None)
    instance_list = []

    if args["balance"] == "true":
        data = ignore_data.balance(data)

    # 过滤阶段保持顺序执行
    filtered_data = [
        row for row in data
        if not should_ignore_row(row, ignore_data, args)
    ]

    # 并行处理阶段
    from mydemo.utils.parallel import batch_process

    def _process_row(row):
        try:
            entry = preprocess_transaction_data(row, owner_id, config=config)
            if ignore_data.empty(entry):
                return None

            if args["balance"] == "true":
                instance = FormatData.balance_instance(entry)
            elif "分期" in row['payment_method']:
                instance = FormatData.installment_instance(entry)
            else:
                instance = FormatData.format_instance(entry, config=config)

            if args["write"] == "true":
                write_entry_to_file(instance)
            return instance
        except ValueError as e:
            return str(e)

    # 根据硬件配置调整参数（建议4-8 workers）
    instance_list = batch_process(
        filtered_data,
        process_func=_process_row,
        max_workers=2 if config.ai_model == "BERT" else min(16, (os.cpu_count() or 4)),
        batch_size=50
    )

    return instance_list


def preprocess_transaction_data(data, owner_id, config=FormatConfig()):
    """
        date : 日期         2023-04-28
        time : 时间         09:03:00
        uuid : 交易单号     1000039801202211266356238708041
        status : 支付状态   WeChat - 支付成功
        amount : 金额       23.00 CNY
        payee : 收款方      浙江古茗
        note : 备注        商品详情
        tag : 标签          # tag
        balacne : 余额     2022-05-01 balance      Liabilities:CreditCard:Bank:CITIC:C0000  -5515.51 CNY
        balance_date =    2024-11-01
        expenditure_sign, account_sign = '+' or '-'
        expense : 支付方式   Expenses:Food:DrinkFruit
        account : 账户      Liabilities:CreditCard:Bank:CITIC:C6428
        commission : 利息   Expenses:Finance:Commission
        installment_granularity : 
        installment_cycle : 
    """
    try:
        expense_handler = ExpenseHandler(data, model=config.ai_model,api_key=config.deepseek_apikey)
        account_handler = AccountHandler(data)
        payee_handler = PayeeHandler(data)
        date = datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        time = datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        uuid = get_uuid(data)
        status = get_status(data)  # 支付状态
        amount = get_amount(data)  # 支付金额
        payee = payee_handler.get_payee(data, owner_id)
        note = get_note(data)
        tag = get_tag(data)  # 标签
        balance = get_balance(data)  # 余额
        balance_date = (datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S") + timedelta(days=1)).strftime("%Y-%m-%d")
        expenditure_sign, account_sign = get_shouzhi(data)
        expense = expense_handler.get_expense(data, owner_id)
        account = account_handler.get_account(data, owner_id)
        commission = get_commission(data)  # 利息
        installment_granularity = get_installment_granularity(data)  # 分期粒度（年/月/日）
        installment_cycle = get_installment_cycle(data)  # 分期频率
        discount = get_discount(data)
        currency = expense_handler.get_currency()
        if data['transaction_type'] == "/":
            actual_amount = calculate_commission(amount, commission)
            return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "note": note,"tag": tag, "balance": balance, "balance_date": balance_date, "expense": expense,"expenditure_sign": expenditure_sign,"account": account, "account_sign": account_sign, "amount": amount, "actual_amount": actual_amount, "installment_granularity": installment_granularity, "installment_cycle": installment_cycle, "discount": discount, "currency": currency}
        return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "note": note,"tag": tag, "balance": balance, "balance_date": balance_date, "expense": expense,"expenditure_sign": expenditure_sign,"account": account, "account_sign": account_sign, "amount": amount, "installment_granularity": installment_granularity, "installment_cycle": installment_cycle, "discount": discount, "currency": currency}
    except ValueError as e:
        raise e


class AccountHandler:
    def __init__(self, data):
        self.key = None
        self.key_list = None
        self.full_list = None
        self.type = None
        self.account = ASSETS_OTHER
        self.bill = data['bill_identifier']
        self.balance = data['transaction_type']

    def initialize_type(self, data):
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, ownerid):
        self.key_list = Assets.objects.filter(owner_id=ownerid, enable=True).values_list('key', flat=True)
        self.full_list = Assets.objects.filter(owner_id=ownerid, enable=True).values_list('full', flat=True)

    def initialize_key(self, data):
        if self.bill == BILL_ALI:
            self.key = alipay_initalize_key(data)
        elif self.bill == BILL_WECHAT:
            self.key = wechatpay_initalize_key(self, data)
        elif self.bill == BILL_CMB_CREDIT:
            self.key = cmb_credit_init_key(data)
        elif self.bill == BILL_BOC_DEBIT:
            self.key = boc_debit_init_key(data)
        elif self.bill == BILL_ICBC_DEBIT:
            self.key = icbc_debit_init_key(data)
        elif self.bill == BILL_CCB_DEBIT:
            self.key = ccb_debit_init_key(data)

    def get_account(self, data, ownerid):
        self.initialize_key(data)
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        self.status = data['transaction_status']
        actual_assets = get_default_assets(ownerid=ownerid)
        account = self.account

        if self.balance == "收入":
            if self.bill == BILL_ALI:
                return alipay_get_income_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_income_account(self, actual_assets, ownerid)
        elif self.balance == "支出":
            if self.bill == BILL_ALI:
                return alipay_get_expense_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_expense_account(self, actual_assets, ownerid)
        elif self.balance == "/" or self.balance == "不计收支":  # 收/支栏 值为/
            if self.bill == BILL_ALI:
                return alipay_get_balance_account(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_balance_account(self, data, actual_assets, ownerid)

        if self.bill == BILL_BOC_DEBIT:
            return boc_debit_get_account(self, ownerid)
        elif self.bill == BILL_CMB_CREDIT:
            return cmb_credit_get_account(self, ownerid)
        elif self.bill == BILL_ICBC_DEBIT:
            return icbc_debit_get_account(self, ownerid)
        elif self.bill == BILL_CCB_DEBIT:
            return ccb_debit_get_account(self, ownerid)
        return account

class SimilarityModel:
    """抽象基类，定义相似度计算接口"""
    def calculate_similarity(self, text: str, candidates: List[str]) -> str:
        raise NotImplementedError

class BertSimilarity(SimilarityModel):
    """BERT相似度计算实现"""
    _tokenizer = None
    _model = None
    _embedding_cache: Dict[str, torch.Tensor] = {}

    @classmethod
    def load_model(cls):
        if cls._model is None:
            local_model_path = Path(__file__).parent.parent.parent / "models" / "bert-base-chinese"
            try:
                cls._tokenizer = BertTokenizer.from_pretrained(local_model_path)
                cls._model = BertModel.from_pretrained(local_model_path)
            except OSError:
                cls._tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
                cls._model = BertModel.from_pretrained('bert-base-chinese')
            cls._model.eval()
        return cls._tokenizer, cls._model

    def _get_embedding(self, text: str) -> torch.Tensor:
        """获取文本嵌入，带缓存"""
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        tokenizer, model = self.load_model()
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=64)
        with torch.no_grad():
            outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:,0,:]
        self._embedding_cache[text] = embedding
        return embedding

    def calculate_similarity(self, text: str, candidates: List[str]) -> str:
        text_embed = self._get_embedding(text)
        similarities = {}

        for candidate in candidates:
            cand_embed = self._get_embedding(candidate)
            similarity = torch.cosine_similarity(text_embed, cand_embed, dim=1)
            similarities[candidate] = similarity.item()

        return max(similarities.items(), key=lambda x: x[1])[0]

class SpacySimilarity(SimilarityModel):
    """spaCy相似度计算实现"""
    _nlp = None

    @classmethod
    def load_model(cls):
        if cls._nlp is None:
            cls._nlp = spacy.load("zh_core_web_md", exclude=["parser", "ner", "lemmatizer"])
        return cls._nlp

    def calculate_similarity(self, text: str, candidates: List[str]) -> str:
        nlp = self.load_model()
        doc = nlp(text)
        similarities = {
            candidate: doc.similarity(nlp(candidate))
            for candidate in candidates
        }
        return max(similarities.items(), key=lambda x: x[1])[0]

class DeepSeekSimilarity(SimilarityModel):
    """DeepSeek API相似度计算实现"""
    def __init__(self, api_key: str, enable_realtime: bool = True):
        self.api_key = api_key
        self.enable_realtime = enable_realtime
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def calculate_similarity(self, text: str, candidates: List[str]) -> str:
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        prompt = f"""请从以下候选列表中选择最匹配文本的条目：
        文本内容：{text}
        候选列表：{", ".join(candidates)}
        只需返回最匹配的候选值，不要任何解释"""

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            return result if result in candidates else candidates[0]
        except Exception as e:
            raise ValueError(f"DeepSeek调用失败，请检查API密钥是否正确")
            # return candidates[0]

class ExpenseHandler:
    def __init__(self, data: Dict, model: str, api_key: Optional[str] = None):
        self.selected_expense_instance = None
        self.selected_income_instance = None
        self.key_list = None
        self.full_list = None
        self.type = None
        self.expend = EXPENSES_OTHER
        self.income = INCOME_OTHER
        self.bill = data['bill_identifier']
        self.balance = data['transaction_type']
        self.time = datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S").time()
        self.currency = "CNY"
        self.model = model

        # 初始化相似度计算模型
        if model == "BERT":
            self.similarity_model = BertSimilarity()
        elif model == "spaCy":
            self.similarity_model = SpacySimilarity()
        elif model == "DeepSeek":
            if not api_key:
                raise ValueError("使用DeepSeek模型需要API密钥")
            self.similarity_model = DeepSeekSimilarity(api_key)
        else:
            self.similarity_model = BertSimilarity()  # 默认使用BERT

    def initialize_type(self, data: Dict) -> None:
        """初始化交易类型"""
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, data: Dict, ownerid: int) -> None:
        """初始化关键字列表"""
        if self.balance == "支出" or "亲情卡" in data['payment_method']:
            self.key_list = Expense.objects.filter(owner_id=ownerid, enable=True).values_list('key', flat=True)
        elif self.balance == "收入":
            self.key_list = Income.objects.filter(owner_id=ownerid, enable=True).values_list('key', flat=True)
        elif self.balance in ("/", "不计收支"):
            self.key_list = Assets.objects.filter(owner_id=ownerid, enable=True).values_list('key', flat=True)
        self.full_list = Assets.objects.filter(owner_id=ownerid, enable=True).values_list('full', flat=True)

    def _resolve_expense_conflict(self, conflict_candidates: List[Tuple[int, object]], transaction_text: str) -> object:
        """解决支出冲突"""
        try:
            selected_key = self.similarity_model.calculate_similarity(
                transaction_text,
                [inst.key for _, inst in conflict_candidates]
            )
            logger.info(f"AI选择结果: 选中关键字 '{selected_key}'，候选列表: {conflict_candidates}")
            return next(inst for _, inst in conflict_candidates if inst.key == selected_key)
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"AI处理失败：{str(e)}")
            raise e
            # 按优先级排序后取第一个
            # sorted_candidates = sorted(conflict_candidates, key=lambda x: (-x[0], len(x[1].key)))
            # return sorted_candidates[0][1]

    def _determine_food_category(self, foodtime: datetime.time) -> str:
        """根据时间确定餐饮类别"""
        if TIME_BREAKFAST_START <= foodtime <= TIME_BREAKFAST_END:
            return ":Breakfast"
        elif TIME_LUNCH_START <= foodtime <= TIME_LUNCH_END:
            return ":Lunch"
        elif TIME_DINNER_START <= foodtime <= TIME_DINNER_END:
            return ":Dinner"
        return ""

    def _process_expense(self, data: Dict, ownerid: int) -> str:
        """处理支出逻辑"""
        matching_keys = [k for k in self.key_list if k in data['counterparty'] or k in data['commodity']]
        conflict_candidates = []
        max_order = None

        for matching_key in matching_keys:
            expense_instance = Expense.objects.filter(owner_id=ownerid, enable=True, key=matching_key).first()
            if expense_instance:
                expend_priority = expense_instance.expend.count(":") * 100
                payee_priority = 50 if expense_instance.payee else 0
                current_order = expend_priority + payee_priority
                conflict_candidates.append((current_order, expense_instance))

                if max_order is None or current_order > max_order:
                    max_order = current_order
                    self.selected_expense_instance = expense_instance

        if len(conflict_candidates) > 1:
            self.selected_expense_instance = self._resolve_expense_conflict(conflict_candidates,
                f"类型：{data['transaction_category']} 商户：{data['counterparty']} 商品：{data['commodity']} 金额：{data['amount']}元")

        if self.selected_expense_instance:
            expend = self.selected_expense_instance.expend
            if expend == "Expenses:Food":
                expend += self._determine_food_category(self.time)
            self.currency = self.selected_expense_instance.currency or "CNY"
            return expend

        return self.expend

    def _process_income(self, data: Dict, ownerid: int) -> str:
        """处理收入逻辑"""
        matching_keys = [k for k in self.key_list if k in data['counterparty'] or k in data['commodity']]
        max_order = None

        for matching_key in matching_keys:
            income_instance = Income.objects.filter(owner_id=ownerid, enable=True, key=matching_key).first()
            if income_instance:
                income_priority = income_instance.income.count(":") * 100
                if max_order is None or income_priority > max_order:
                    max_order = income_priority
                    self.selected_income_instance = income_instance

        return self.selected_income_instance.income if self.selected_income_instance else self.income

    def get_expense(self, data: Dict, ownerid: int) -> str:
        """主处理方法"""
        self.initialize_key_list(data, ownerid)
        self.initialize_type(data)

        if self.balance == "支出" or "亲情卡" in data['payment_method']:
            return self._process_expense(data, ownerid)
        elif self.balance == "收入":
            return self._process_income(data, ownerid)
        elif self.balance in ("/", "不计收支"):
            actual_assets = get_default_assets(ownerid=ownerid)
            if self.bill == BILL_ALI:
                return alipay_get_balance_expense(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                return wechatpay_get_balance_expense(self, data, actual_assets, ownerid)

        return self.expend

    def get_currency(self):
        return self.currency


class PayeeHandler:
    def __init__(self, data):
        self.key_list = None
        self.payee = data['counterparty']
        self.notes = data['commodity']
        self.bill = data['bill_identifier']

    def get_payee(self, data, ownerid): #TODO
        self.key_list = list(Expense.objects.filter(owner_id=ownerid, enable=True).values_list('key', flat=True))
        if data['bill_identifier'] == BILL_WECHAT and data['transaction_type'] == "/" and data['transaction_category'] == "信用卡还款":
            return data['counterparty']
        elif data['bill_identifier'] == BILL_WECHAT and data['transaction_type'] == "/":  # 一般微信好友转账，如妈妈->我
            return data['payment_method'][:4]
        elif data['transaction_category'] == "微信红包（单发）":
            return self.payee[2:]
        elif data['transaction_category'] == "转账-退款" or data['transaction_category'] == "微信红包-退款":
            return "退款"
        elif '(' in self.payee and ')' in self.payee and self.notes == "Transfer":
            match = re.search(r'\((.*?)\)', self.payee)  # 提取 account 中的数字部分
            if match:
                return match.group(1)
        else:
            return self.general_payee(data, ownerid)

    def general_payee(self, data, ownerid):
        payee = self.payee
        matching_keys = [k for k in self.key_list if k in self.payee or k in self.notes]  # 通过列表推导式获取所有匹配的key形成新的列表
        max_order = None
        for matching_key in matching_keys:  # 遍历所有匹配的key，获取最大的优先级
            expense_instance = Expense.objects.filter(owner_id=ownerid, enable=True, key=matching_key).first()
            if expense_instance:  # 通过Expenses及Payee计算优先级
                expend_instance_priority = expense_instance.expend.count(":") * 100
                payee_instance_priority = 50 if expense_instance.payee else 0
                matching_max_order = expend_instance_priority + payee_instance_priority

            if matching_max_order is not None and (
                    max_order is None or matching_max_order > max_order):  # 如果匹配到的key的matching_max_order大于max_order，则更新max_order
                max_order = matching_max_order

                if expense_instance is not None and expense_instance.payee is not None and expense_instance.payee != '':
                    payee = expense_instance.payee

            # 如果匹配到的key的matching_max_order等于max_order，则取原始payee。这样做的目的是为了防止多个key的matching_max_order相同，但payee不同的情况
            # 原本是想要多个payee一起展示方便选择，但是实际发现实现较复杂。如果最大优先级冲突，则将payee更新为原始payee.
            elif matching_max_order is not None and (max_order is None or matching_max_order == max_order):
                payee = self.payee

        if data['bill_identifier'] == BILL_ALI and payee == "":
            return data['counterparty']
        elif data['bill_identifier'] == BILL_WECHAT and payee == "":
            payee = data['counterparty']
            if payee == "/":
                return data['transaction_time']
        return payee


def calculate_commission(total, commission):
    if commission != "":
        amount = "{:.2f}".format(float(total.split()[0]) - float(commission.split()[0]))
    else:
        amount = total
    return amount


def get_shouzhi(data): #TODO
    shouzhi = data['transaction_type']
    high = ""
    loss = "-"

    if shouzhi == "支出":
        return high, loss
    elif shouzhi == "收入":
        return loss, high
    elif shouzhi in ["/", "不计收支"]:
        if data['bill_identifier'] == BILL_ALI:
            if data['commodity'] == "信用卡还款":
                return high, loss
            elif "亲情卡" in data['payment_method']:
                return high, loss
            elif (re.match(pattern["花呗自动还款"], data['commodity'])) or (re.match(pattern["花呗主动还款"], data['commodity'])):
                    return high, loss
            elif "放款成功" in  data['transaction_status']:
                return loss, high
            elif "还款成功" in  data['transaction_status']:
                return high, loss
            elif ("买入" in data['commodity']) or ("公司" in data['counterparty']):  #TODO  # 目前没找到更合理的规律
                return high,loss
        if data['bill_identifier'] == BILL_WECHAT and data['transaction_category'] == "信用卡还款":
            return high, loss
        return loss, high
    else:
        return None, None


def get_attribute(data, attribute_handlers):
    # 如果需要对数据进行一般性处理，也可以在这里完成

    bill_type = data['bill_identifier']
    if bill_type in attribute_handlers:
        return attribute_handlers[bill_type](data)
    return None


def get_uuid(data):
    uuid_handlers = {
        BILL_ALI: alipay_get_uuid,
        BILL_WECHAT: wechatpay_get_uuid,
    }
    return get_attribute(data, uuid_handlers)


def get_status(data):
    status_handlers = {
        BILL_ALI: alipay_get_status,
        BILL_WECHAT: wechatpay_get_status,
        BILL_CMB_CREDIT: cmb_credit_get_status,
        BILL_BOC_DEBIT: boc_debit_get_status,
        BILL_ICBC_DEBIT:icbc_debit_get_status,
        BILL_CCB_DEBIT:ccb_debit_get_status,
    }
    return get_attribute(data, status_handlers)


def get_note(data):
    notes_handlers = {
        BILL_ALI: alipay_get_note,
        BILL_WECHAT: wechatpay_get_note,
        BILL_CMB_CREDIT: cmb_credit_get_note,
        BILL_BOC_DEBIT: boc_debit_get_note,
        BILL_ICBC_DEBIT:icbc_debit_get_note,
        BILL_CCB_DEBIT:ccb_debit_get_note,
    }
    data['commodity'] = data['commodity'].replace('"', '\\"')
    return get_attribute(data, notes_handlers)


def get_amount(data):
    amount_handlers = {
        BILL_ALI: alipay_get_amount,
        BILL_WECHAT: wechatpay_get_amount,
        BILL_CMB_CREDIT: cmb_credit_get_amount,
        BILL_BOC_DEBIT: boc_debit_get_amount,
        BILL_ICBC_DEBIT: icbc_debit_get_amount,
        BILL_CCB_DEBIT:ccb_debit_get_amount,
    }
    return get_attribute(data, amount_handlers)


def get_tag(data):
    tag_handlers = {
        BILL_ALI: alipay_get_tag,
        BILL_WECHAT: wechatpay_get_tag,
    }
    return get_attribute(data, tag_handlers)


def get_balance(data):
    balance_handlers = {
        BILL_BOC_DEBIT: boc_debit_get_balance,
        BILL_ICBC_DEBIT: icbc_debit_get_balance,
        BILL_CCB_DEBIT:ccb_debit_get_balance,
    }
    return get_attribute(data, balance_handlers)


def get_commission(data):
    commission_handlers = {
        BILL_ALI: alipay_get_commission,
        BILL_WECHAT: wechatpay_get_commission,
    }
    return get_attribute(data, commission_handlers)


def get_installment_granularity(data):
    installment_granularity_handlers = {
        BILL_ALI: alipay_installment_granularity,
    }
    return get_attribute(data, installment_granularity_handlers)


def get_installment_cycle(data):
    installment_cycle_handlers = {
        BILL_ALI: alipay_installment_cycle,
    }
    return get_attribute(data, installment_cycle_handlers)

def get_discount(data):
    tag_handlers = {
        BILL_ALI: alipay_get_discount,
        BILL_WECHAT: wechatpay_get_discount,
    }
    return get_attribute(data, tag_handlers)