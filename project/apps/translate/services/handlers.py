import datetime
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from maps.models import Expense, Income
from translate.utils import *
from translate.views.AliPay import *
from translate.views.WeChat import *
from translate.views.BOC_Debit import *
from translate.views.CMB_Credit import *
from translate.views.ICBC_Debit import *
from translate.views.CCB_Debit import *
from translate.services.similarity import BertSimilarity, SpacySimilarity, DeepSeekSimilarity


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

        if len(conflict_candidates) > 1 and self.model != "None":
            self.selected_expense_instance = self._resolve_expense_conflict(conflict_candidates,
                f"类型：{data['transaction_category']} 商户：{data['counterparty']} 商品：{data['commodity']} 金额：{data['amount']}元")
        elif len(conflict_candidates) > 1 and self.model == "None":
            # 根据expend和payee规则计算优先级，如果最高的冲突，则选择第一个并输出日志，日志内容包括候选列表和选中结果还有优先级
            sorted_candidates = sorted(conflict_candidates, key=lambda x: (-x[0], len(x[1].key)))
            self.selected_expense_instance = sorted_candidates[0][1]
            logger.info(f"无AI选择结果: 选中关键字 '{self.selected_expense_instance.key}'，候选列表: {conflict_candidates}")

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
