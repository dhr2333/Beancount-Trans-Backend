# project/apps/translate/services/parse/transaction_parser.py
from datetime import timedelta, datetime
from typing import Dict
from translate.services.handlers import AccountHandler, ExpenseHandler, PayeeHandler
from translate.services.handlers import get_shouzhi, get_uuid, get_status, get_amount, get_note, get_tag, get_balance, get_commission, get_installment_granularity, get_installment_cycle, get_discount


def single_parse_transaction(row: Dict, owner_id: int, config: Dict, selected_key: str) -> Dict:
    """解析单条交易记录

    Args:
        row (Dict): 单条初始化后的交易记录
        owner_id (int): 使用该用户的Map映射记录
        config (Dict): 用户配置信息

    Returns:
        Dict: 解析后的交易记录
    """
    try:
        expense_handler = ExpenseHandler(row, model=config.ai_model, api_key=config.deepseek_apikey, selected_key=selected_key)
        account_handler = AccountHandler(row)
        payee_handler = PayeeHandler(row)
        date = datetime.strptime(row['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        flag = config.flag
        time = datetime.strptime(row['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        uuid = get_uuid(row)
        status = get_status(row)
        amount = get_amount(row)
        payee = payee_handler.get_payee(row, owner_id)
        note = get_note(row)
        tag = get_tag(row)
        balance = get_balance(row)
        balance_date = (datetime.strptime(row['transaction_time'], "%Y-%m-%d %H:%M:%S") + timedelta(days=1)).strftime("%Y-%m-%d")
        expenditure_sign, account_sign = get_shouzhi(row)
        expense,selected_expense_key, expense_candidates_with_score = expense_handler.get_expense(row, owner_id)
        account = account_handler.get_account(row, owner_id)
        commission = get_commission(row)
        installment_granularity = get_installment_granularity(row)
        installment_cycle = get_installment_cycle(row)
        discount = get_discount(row)
        currency = expense_handler.get_currency()

        # 根据beancount规范重新制订返回的字段
        # result = {
        #     "date": date, # 交易日期
        #     "transactions": flag,  # 交易（如"*":交易已完成，金额已知 "!":交易不完整，需要确认或修改）
        #     "time": time,  # 元属性:交易时间
        #     "uuid": uuid,  # 元属性:唯一标识符(部分账单未提供)
        #     "status": status,  # 元属性:交易状态(如交易完成、退款成功等)
        #     "payee": payee,  # 收款人或付款人
        #     "narration": note,  # 备注信息
        #     "tags": tag,  # 标签信息
        #     "links": None,  # 链接信息(如有)
        #     "balance_assertions": balance,  # 平衡断言
        #     "balance_assertions_date": balance_date,  # 平衡断言日期
        #     "expense_account": expense,  # 账户支出/收入类型(如餐饮、购物、收到红包等)
        #     "expense_sign": expenditure_sign,  # 收支标志(如收入为"-"、支出为"+"，遵循复式记账原则)
        #     "asset_account": account,  # 账户名称
        #     "asset_sign": account_sign,  # 账户标志(如收入为"+"、支出为"-"，遵循复式记账原则)
        #     "cost": None,  # 成本(如有)
        #     "prices": amount,  # 交易金额
        #     "installment_granularity": installment_granularity,  # 分期粒度(如月、周等)
        #     "installment_cycle": installment_cycle,  # 分期周期(如每月、每周等)
        #     "discount": discount,  # 折扣信息
        #     "currencies": currency,  # 交易货币
        #     "selected_expense_key": selected_expense_key,  # AI模型选择的映射关键字
        #     "expense_candidates_with_score": expense_candidates_with_score  # AI模型返回的候选支出类型及其分数
        # }
        result = {
            "date": date,
            "time": time,
            "uuid": uuid,
            "status": status,
            "payee": payee,
            "note": note,
            "tag": tag,
            "balance": balance,
            "balance_date": balance_date,
            "expense": expense,
            "expenditure_sign": expenditure_sign,
            "account": account,
            "account_sign": account_sign,
            "amount": amount,
            "installment_granularity": installment_granularity,
            "installment_cycle": installment_cycle,
            "discount": discount,
            "currency": currency,
            "selected_expense_key": selected_expense_key,
            "expense_candidates_with_score":expense_candidates_with_score
        }
        if row['transaction_type'] == "/":
            actual_amount  = "{:.2f}".format(float(amount.split()[0]) - float(commission.split()[0])) if commission != "" else amount
            result["actual_amount"] = actual_amount  # 实际交易金额(扣除佣金后的金额)

        return result
    except ValueError as e:
        raise e