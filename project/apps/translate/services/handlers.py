# project/apps/translate/services/handlers.py
import datetime
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from project.apps.maps.models import Expense, Income
from project.apps.translate.utils import *
from project.apps.translate.views.AliPay import *
from project.apps.translate.views.WeChat import *
from project.apps.translate.views.BOC_Debit import *
from project.apps.translate.views.CMB_Credit import *
from project.apps.translate.views.ICBC_Debit import *
from project.apps.translate.views.CCB_Debit import *
from project.apps.translate.services.similarity import BertSimilarity, SpacySimilarity, DeepSeekSimilarity
from project.apps.translate.services.mapping_provider import get_mapping_provider
import logging


logger = logging.getLogger(__name__)

class AccountHandler:
    def __init__(self, data):
        self.key = None
        self.key_list = None
        self.full_list = None
        self.type = None
        self.account = ASSETS_OTHER
        self.bill = data['bill_identifier']
        self.balance = data['transaction_type']
        self.selected_asset_instance = None  # 新增：存储选中的资产映射实例
        self.asset_tags = []  # 新增：存储资产映射关联的标签
        self._asset_mappings = []  # 缓存资产映射数据

    def find_asset_by_key(self, key: str):
        """根据 key 查找资产映射"""
        return next((m for m in self._asset_mappings if m.key == key), None)

    def find_asset_by_full(self, full: str):
        """根据 full 查找资产映射"""
        return next((m for m in self._asset_mappings if m.full == full), None)

    def initialize_type(self, data):
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, ownerid):
        # 使用映射数据提供者获取资产映射
        provider = get_mapping_provider(ownerid)
        asset_mappings = provider.get_asset_mappings(enable_only=True)
        self.key_list = [m.key for m in asset_mappings]
        self.full_list = [m.full for m in asset_mappings]
        self._asset_mappings = asset_mappings  # 缓存以供后续使用

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

    def _load_asset_tags(self, asset_key: str, ownerid: int) -> None:
        """加载资产映射关联的标签"""
        try:
            # 从缓存的映射数据中查找
            asset_instance = next((m for m in self._asset_mappings if m.key == asset_key), None)
            if asset_instance:
                self.selected_asset_instance = asset_instance
                self.asset_tags = list(asset_instance.tags.filter(enable=True))
        except Exception as e:
            logger.error(f"加载资产标签失败: {str(e)}")
            self.asset_tags = []

    def get_asset_tags(self):
        """获取资产映射的标签列表"""
        return self.asset_tags

    def get_account(self, data, ownerid):
        self.initialize_key(data)
        self.initialize_key_list(ownerid)  # 根据收支情况获取数据库中key的所有值，将其处理为列表
        self.initialize_type(data)
        self.status = data['transaction_status']
        actual_assets = get_default_assets(ownerid=ownerid)
        account = self.account

        if self.balance == "收入":
            if self.bill == BILL_ALI:
                account = alipay_get_income_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                account = wechatpay_get_income_account(self, actual_assets, ownerid)
        elif self.balance == "支出":
            if self.bill == BILL_ALI:
                account = alipay_get_expense_account(self, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                account = wechatpay_get_expense_account(self, actual_assets, ownerid)
        elif self.balance == "/" or self.balance == "不计收支":  # 收/支栏 值为/
            if self.bill == BILL_ALI:
                account = alipay_get_balance_account(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                account = wechatpay_get_balance_account(self, data, actual_assets, ownerid)
        elif self.bill == BILL_BOC_DEBIT:
            account = boc_debit_get_account(self, ownerid)
        elif self.bill == BILL_CMB_CREDIT:
            account = cmb_credit_get_account(self, ownerid)
        elif self.bill == BILL_ICBC_DEBIT:
            account = icbc_debit_get_account(self, ownerid)
        elif self.bill == BILL_CCB_DEBIT:
            account = ccb_debit_get_account(self, ownerid)

        # 加载资产标签
        if self.key and self.key in self.key_list:
            self._load_asset_tags(self.key, ownerid)

        return account


class ExpenseHandler:
    def __init__(self, data: Dict, model: str, api_key: Optional[str] = None, selected_key: Optional[str] = None):
        self.selected_expense_instance = None
        self.selected_income_instance = None
        self.selected_key = selected_key
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
        self.selected_expense_key = None
        self.expense_candidates_with_score = []  # 如果你想带分数
        self.mapping_tags = []  # 新增：存储映射关联的标签
        self.all_candidates_tags = []  # 新增：存储所有候选映射的标签
        self._expense_mappings = []  # 缓存支出映射数据
        self._income_mappings = []  # 缓存收入映射数据
        self._asset_mappings = []  # 缓存资产映射数据

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

    def find_asset_by_key(self, key: str):
        """根据 key 查找资产映射"""
        return next((m for m in self._asset_mappings if m.key == key), None)

    def find_asset_by_full(self, full: str):
        """根据 full 查找资产映射"""
        return next((m for m in self._asset_mappings if m.full == full), None)

    def initialize_type(self, data: Dict) -> None:
        """初始化交易类型"""
        if self.bill == BILL_ALI:
            self.type = alipay_get_type(data)
        elif self.bill == BILL_WECHAT:
            self.type = wechatpay_get_type(data)

    def initialize_key_list(self, data: Dict, ownerid: int) -> None:
        """初始化关键字列表"""
        provider = get_mapping_provider(ownerid)

        if self.balance == "支出" or "亲情卡" in data['payment_method']:
            expense_mappings = provider.get_expense_mappings(enable_only=True)
            self.key_list = [m.key for m in expense_mappings]
            self._expense_mappings = expense_mappings  # 缓存
        elif self.balance == "收入":
            income_mappings = provider.get_income_mappings(enable_only=True)
            self.key_list = [m.key for m in income_mappings]
            self._income_mappings = income_mappings  # 缓存
        elif self.balance in ("/", "不计收支"):
            asset_mappings = provider.get_asset_mappings(enable_only=True)
            self.key_list = [m.key for m in asset_mappings]
            self._asset_mappings = asset_mappings  # 缓存

        # full_list 用于资产查询，如果还没缓存资产映射，则获取并缓存
        if not self._asset_mappings:
            self._asset_mappings = provider.get_asset_mappings(enable_only=True)
        self.full_list = [m.full for m in self._asset_mappings]

    def _resolve_expense_conflict(self, conflict_candidates: List[Tuple[int, object]], transaction_text: str):
        try:
            keys = [inst.key for _, inst in conflict_candidates]
            sim_result = self.similarity_model.calculate_similarity(transaction_text, keys)  # 使用相似度模型计算相似度
            selected_key = sim_result["best_match"]
            # self.similarity_model.collect_training_data(transaction_text, keys, selected_key)  # AI反馈数据收集
            scores = sim_result["scores"]
            # logger.info(f"AI选择结果: 选中关键字 '{selected_key}'，候选列表: {conflict_candidates}")
            self.selected_expense_key = selected_key
            # 将候选项和分数存储到实例变量中
            # 生成候选项列表，包含分数
            # 这里的分数是相似度分数，保留四位小数
            self.expense_candidates_with_score = [
                {
                    "key": inst.key,
                    "score": round(scores.get(inst.key, 0), 4)
                }
                for _, inst in conflict_candidates
            ]
            return next(inst for _, inst in conflict_candidates if inst.key == selected_key)
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
            # 从缓存的映射数据中查找
            expense_instance = next((m for m in self._expense_mappings if m.key == matching_key), None)
            if expense_instance and expense_instance.expend:
                expend_priority = expense_instance.expend.account.count(":") * 100
                payee_priority = 50 if expense_instance.payee else 0
                current_order = expend_priority + payee_priority
                conflict_candidates.append((current_order, expense_instance))

                if max_order is None or current_order > max_order:
                    max_order = current_order
                    self.selected_expense_instance = expense_instance

        # 收集所有候选映射的标签
        if len(conflict_candidates) > 0:
            self._load_all_candidates_tags(conflict_candidates)

        if len(conflict_candidates) > 1 and self.model != "None":
            selected_instance = self._resolve_expense_conflict(conflict_candidates,
                f"类型：{data['transaction_category']} 商户：{data['counterparty']} 商品：{data['commodity']} 金额：{data['amount']}元")  # 构造语义化查询
            self.selected_expense_instance = selected_instance
            self.selected_expense_key = selected_instance.key
        else:
            # 只有一个候选或无候选，直接给分数
            self.expense_candidates_with_score = [
                {
                    "key": inst.key,
                    "score": 1.0
                }
                for _, inst in conflict_candidates
            ]
            if self.selected_expense_instance:
                self.selected_expense_key = self.selected_expense_instance.key

        if self.selected_expense_instance:
            # 获取映射关联的标签
            self._load_mapping_tags(self.selected_expense_instance)

            if self.selected_key:
                # 从缓存的映射数据中查找
                self.selected_expense_instance = next((m for m in self._expense_mappings if m.key == self.selected_key), None)
                if self.selected_expense_instance:
                    self._load_mapping_tags(self.selected_expense_instance)
                    if self.selected_expense_instance.expend:
                        expend = self.selected_expense_instance.expend.account
                        if expend == "Expenses:Food":
                            expend += self._determine_food_category(self.time)
                        self.currency = self.selected_expense_instance.currency if self.selected_expense_instance.currency else "CNY"
                        return expend, self.selected_key, self.expense_candidates_with_score
            elif self.selected_key is None:
                if self.selected_expense_instance and self.selected_expense_instance.expend:
                    expend = self.selected_expense_instance.expend.account
                    if expend == "Expenses:Food":
                        expend += self._determine_food_category(self.time)
                    self.currency = self.selected_expense_instance.currency if self.selected_expense_instance.currency else "CNY"
                    return expend, self.selected_expense_key, self.expense_candidates_with_score

        return self.expend, self.selected_expense_key, self.expense_candidates_with_score

    def _load_mapping_tags(self, mapping_instance):
        """加载映射关联的标签"""
        try:
            self.mapping_tags = list(mapping_instance.tags.filter(enable=True))
        except Exception as e:
            logger.error(f"加载映射标签失败: {str(e)}")
            self.mapping_tags = []

    def _load_all_candidates_tags(self, conflict_candidates: List[Tuple[int, object]]):
        """加载所有候选映射的标签"""
        try:
            all_tags = []
            for _, instance in conflict_candidates:
                tags = list(instance.tags.filter(enable=True))
                all_tags.extend(tags)
            # 去重，保持标签对象唯一性
            seen_tag_ids = set()
            unique_tags = []
            for tag in all_tags:
                if tag.id not in seen_tag_ids:
                    seen_tag_ids.add(tag.id)
                    unique_tags.append(tag)
            self.all_candidates_tags = unique_tags
        except Exception as e:
            logger.error(f"加载候选标签失败: {str(e)}")
            self.all_candidates_tags = []

    def get_mapping_tags(self):
        """获取当前映射的标签列表"""
        return self.mapping_tags

    def get_all_candidates_tags(self):
        """获取所有候选映射的标签列表"""
        return self.all_candidates_tags

    def _process_income(self, data: Dict, ownerid: int) -> str:
        """处理收入逻辑"""
        matching_keys = [k for k in self.key_list if k in data['counterparty'] or k in data['commodity']]
        max_order = None
        income_candidates = []

        for matching_key in matching_keys:
            # 从缓存的映射数据中查找
            income_instance = next((m for m in self._income_mappings if m.key == matching_key), None)
            if income_instance and income_instance.income:
                income_priority = income_instance.income.account.count(":") * 100
                income_candidates.append(income_instance)
                if max_order is None or income_priority > max_order:
                    max_order = income_priority
                    self.selected_income_instance = income_instance

        # 收集所有收入候选的标签
        if income_candidates:
            try:
                all_tags = []
                for instance in income_candidates:
                    tags = list(instance.tags.filter(enable=True))
                    all_tags.extend(tags)
                # 去重
                seen_tag_ids = set()
                unique_tags = []
                for tag in all_tags:
                    if tag.id not in seen_tag_ids:
                        seen_tag_ids.add(tag.id)
                        unique_tags.append(tag)
                self.all_candidates_tags = unique_tags
            except Exception as e:
                logger.error(f"加载收入标签失败: {str(e)}")
                self.all_candidates_tags = []

        if self.selected_income_instance and self.selected_income_instance.income:
            return self.selected_income_instance.income.account
        return self.income

    def get_expense(self, data: Dict, ownerid: int) -> str:
        """主处理方法"""
        self.initialize_key_list(data, ownerid)
        self.initialize_type(data)

        if self.balance == "支出" or "亲情卡" in data['payment_method']:
            expend, selected_expense_key, expense_candidates_with_score = self._process_expense(data, ownerid)
            return expend, selected_expense_key, expense_candidates_with_score
        elif self.balance == "收入":
            income = self._process_income(data, ownerid)
            return income, None, []
        elif self.balance in ("/", "不计收支"):
            actual_assets = get_default_assets(ownerid=ownerid)
            if self.bill == BILL_ALI:
                expend = alipay_get_balance_expense(self, data, actual_assets, ownerid)
            elif self.bill == BILL_WECHAT:
                expend = wechatpay_get_balance_expense(self, data, actual_assets, ownerid)
            else:
                expend = self.expend
            return expend, None, []
        return self.expend, None, []

    def get_currency(self) -> str:
        return self.currency


class PayeeHandler:
    def __init__(self, data):
        self.key_list = None
        self.payee = data['counterparty']
        self.notes = data['commodity']
        self.bill = data['bill_identifier']
        self._expense_mappings = []  # 缓存映射数据

    def get_payee(self, data, ownerid): #TODO
        # 使用映射数据提供者
        provider = get_mapping_provider(ownerid)
        expense_mappings = provider.get_expense_mappings(enable_only=True)
        self.key_list = [m.key for m in expense_mappings]
        self._expense_mappings = expense_mappings
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
            # 从缓存的映射数据中查找
            expense_instance = next((m for m in self._expense_mappings if m.key == matching_key), None)
            matching_max_order = None  # 每次循环初始化
            if expense_instance and expense_instance.expend:  # 通过Expenses及Payee计算优先级
                expend_instance_priority = expense_instance.expend.account.count(":") * 100
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
