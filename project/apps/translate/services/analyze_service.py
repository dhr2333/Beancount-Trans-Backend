import csv
import os
import datetime
from datetime import timedelta
from datetime import datetime
from translate.services.handlers import AccountHandler, ExpenseHandler, PayeeHandler
from translate.services.handlers import get_shouzhi, get_uuid, get_status, get_amount, get_note, get_tag, get_balance, get_commission, get_installment_granularity, get_installment_cycle, get_discount
from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.utils.file import create_temporary_file, file_convert_to_csv, write_entry_to_file
from translate.utils import *
from translate.views.AliPay import *
from translate.views.WeChat import *
from translate.views.BOC_Debit import *
from translate.views.CMB_Credit import *
from translate.views.ICBC_Debit import *
from translate.views.CCB_Debit import *


class AnalyzeService:
    def __init__(self, owner_id, config):
        self.owner_id = owner_id
        self.config = config
        self.selected_expense_key = None
        self.expense_candidates = []

    def analyze(self, uploaded_file, args):
        try:
            csv_file = file_convert_to_csv(uploaded_file, args.get("password", ""))
            temp, encoding = create_temporary_file(csv_file)
        except (DecryptionError, UnsupportedFileTypeError) as e:
            raise e

        if args.get('isCSVOnly', False):
            with open(temp.name, newline='', encoding=encoding) as csvfile:
                csv_content = csvfile.read()
            os.unlink(temp.name)
            return {'csv': csv_content}

        try:
            with open(temp.name, newline='', encoding=encoding, errors="ignore") as csvfile:
                bill_list = self.get_initials_bill(csv.reader(csvfile))
            result_list = self.beancount_outfile(bill_list, self.owner_id, args, self.config)
        finally:
            if os.path.exists(temp.name):
                os.unlink(temp.name)

        results = []
        for entry in result_list:
            if isinstance(entry, dict):
                results.append({
                    "id": entry.get("uuid") or entry.get("流水号") or str(hash(str(entry))),
                    "formatted": entry.get("formatted"),
                    "ai_choose": entry.get("selected_expense_key"),
                    "ai_candidates": entry.get("expense_candidates_with_score", []),
                })
            else:
                results.append({
                    "id": str(hash(str(entry))),
                    "formatted": entry,
                    "ai_choose": None,
                    "ai_candidates": [],
                })

        return {
            "results": results,
            "summary": {"count": len(results)},
            "status": "success"
        }

    def get_initials_bill(self, bill):
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

    def should_ignore_row(self, row, ignore_data, args):
        return (ignore_data.wechatpay_ignore(row)
                or ignore_data.alipay_ignore(row)
                or ignore_data.alipay_fund_ignore(row)
                or ignore_data.cmb_credit_ignore(row, args.get("cmb_credit_ignore"))
                or ignore_data.boc_debit_ignore(row, args.get("boc_debit_ignore")))

    def beancount_outfile(self, data, owner_id: int, args, config):
        # 并行处理
        ignore_data = IgnoreData(None)
        instance_list = []

        if args["balance"] is True:
            data = ignore_data.balance(data)
        filtered_data = [
            row for row in data if not self.should_ignore_row(row, ignore_data, args)
        ]

        from project.utils.parallel import batch_process

        def _process_row(row):
            try:
                entry = self.preprocess_transaction_data(row, owner_id, config=config)
                if ignore_data.empty(entry):
                    return None

                if args["balance"] is True:
                    formatted = FormatData.balance_instance(entry)
                elif "分期" in row['payment_method']:
                    formatted = FormatData.installment_instance(entry)
                else:
                    formatted = FormatData.format_instance(entry, config=config)
                if args["write"] is True:
                    write_entry_to_file(formatted)
                # 返回结构化数据
                return {
                    "formatted": formatted,
                    "selected_expense_key": entry.get("selected_expense_key"),
                    "expense_candidates_with_score": entry.get("expense_candidates_with_score", []),
                    "uuid": entry.get("uuid"),
                }
            except Exception as e:
                raise RuntimeError(f"Error processing row {row.get('流水号', 0)}: {e}")

        # 根据硬件配置调整参数（建议4-8 workers）
        instance_list = batch_process(
            filtered_data,
            process_func=_process_row,
            max_workers= 1 if config.ai_model == "BERT" else min(16, (os.cpu_count() or 4)),
            batch_size=50
        )

        return instance_list

    def preprocess_transaction_data(self, data, owner_id, config=FormatConfig()):
        try:
            expense_handler = ExpenseHandler(data, model=config.ai_model, api_key=config.deepseek_apikey)
            account_handler = AccountHandler(data)
            payee_handler = PayeeHandler(data)
            date = datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            time = datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            uuid = get_uuid(data)
            status = get_status(data)
            amount = get_amount(data)
            payee = payee_handler.get_payee(data, owner_id)
            note = get_note(data)
            tag = get_tag(data)
            balance = get_balance(data)
            balance_date = (datetime.strptime(data['transaction_time'], "%Y-%m-%d %H:%M:%S") + timedelta(days=1)).strftime("%Y-%m-%d")
            expenditure_sign, account_sign = get_shouzhi(data)
            expense,selected_expense_key, expense_candidates_with_score = expense_handler.get_expense(data, owner_id)
            account = account_handler.get_account(data, owner_id)
            commission = get_commission(data)
            installment_granularity = get_installment_granularity(data)
            installment_cycle = get_installment_cycle(data)
            discount = get_discount(data)
            currency = expense_handler.get_currency()
            if data['transaction_type'] == "/":
                actual_amount = self.calculate_commission(amount, commission)
                return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "note": note, "tag": tag, "balance": balance, "balance_date": balance_date, "expense": expense, "expenditure_sign": expenditure_sign, "account": account, "account_sign": account_sign, "amount": amount, "actual_amount": actual_amount, "installment_granularity": installment_granularity, "installment_cycle": installment_cycle, "discount": discount, "currency": currency, "selected_expense_key": selected_expense_key, "expense_candidates_with_score":expense_candidates_with_score}
            return {"date": date, "time": time, "uuid": uuid, "status": status, "payee": payee, "note": note, "tag": tag, "balance": balance, "balance_date": balance_date, "expense": expense, "expenditure_sign": expenditure_sign, "account": account, "account_sign": account_sign, "amount": amount, "installment_granularity": installment_granularity, "installment_cycle": installment_cycle, "discount": discount, "currency": currency, "selected_expense_key": selected_expense_key, "expense_candidates_with_score":expense_candidates_with_score}
        except ValueError as e:
            raise e

    def calculate_commission(self, total, commission):
        if commission != "":
            amount = "{:.2f}".format(float(total.split()[0]) - float(commission.split()[0]))
        else:
            amount = total
        return amount
