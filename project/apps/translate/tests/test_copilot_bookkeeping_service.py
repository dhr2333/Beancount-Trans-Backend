"""CopilotBookkeepingService Copilot 记账暂存区服务单元测试

覆盖：
- 支出 / 收入 / 转账条目文本与 signs（支出账户正、资金账户负；收入相反；转账转出负转入正）
- 条目结构（tag_details / 合成 original_row / 去重字段）
- 暂存区创建与追加（review_expires_at 追加不延长）
- 入队 ref 形态（source='copilot'、file_id=None）与 entry_review 待办激活
- 与队列中已存在条目重复时跳过
- 字段 / 账户 / 币种 / 标签非法时逐条跳过并返回 1 起始 index 的错误
- 超出条数上限整体拒绝

去重服务的 LLM 判定统一被 mock 为不可用，保证测试确定性且不产生网络调用。
"""
import time

import pytest
from django.core.cache import cache
from django.test import override_settings

from project.apps.account.models import Account
from project.apps.reconciliation.models import ScheduledTask
from project.apps.tags.models import Tag
from project.apps.translate.services.copilot_bookkeeping_service import (
    CopilotBookkeepingService,
)
from project.apps.translate.services.entry_dedup_service import EntryDedupService
from project.apps.translate.services.entry_review_queue_service import (
    EntryReviewQueueService,
)
from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.translate.utils.beancount_validator import BeancountValidator


EXPENSE_ACCOUNT = 'Expenses:Shopping:Food'
INCOME_ACCOUNT = 'Income:Salary'
ASSET_ACCOUNT = 'Assets:Bank:CMB'
ASSET_WALLET = 'Assets:Wallet'
LIABILITY_ACCOUNT = 'Liabilities:CreditCard:CMB'
TAG_PATH = 'Category/Food'

_ACCOUNT_MISSING_MESSAGE = '账户不在用户账户目录中，请先调用 get_ledger_context 核对或询问用户'


def _entry(**fields):
    """构造一笔 create_entries 入参（默认合法支出）。"""
    entry_type = fields.get('type', 'expense')
    base = {
        'type': entry_type,
        'date': '2025-01-20',
        'amount': 35.0,
        'narration': '午餐',
        'payee': '食堂',
    }
    if entry_type == 'expense':
        base.update({'account': EXPENSE_ACCOUNT, 'payment_account': ASSET_ACCOUNT})
    elif entry_type == 'income':
        base.update({'account': INCOME_ACCOUNT, 'payment_account': ASSET_ACCOUNT})
    elif entry_type == 'transfer':
        base.update({'from_account': ASSET_ACCOUNT, 'to_account': ASSET_WALLET})
    base.update(fields)
    return base


@pytest.fixture
def accounts(user):
    """创建可用的账户目录（含父子自动补齐）。"""
    for path in (
        EXPENSE_ACCOUNT,
        INCOME_ACCOUNT,
        ASSET_ACCOUNT,
        ASSET_WALLET,
        LIABILITY_ACCOUNT,
    ):
        Account.objects.create(account=path, owner=user)
    return user


@pytest.fixture
def tag(user):
    """创建一个启用标签（完整路径 Category/Food）。"""
    return Tag.objects.create(name=TAG_PATH, owner=user)


@pytest.fixture(autouse=True)
def _disable_dedup_llm(monkeypatch):
    """令去重服务的 LLM 判定不可用，回退到确定性精确匹配。"""
    monkeypatch.setattr(EntryDedupService, '_llm_judge_pairs', lambda user, pairs: None)


@pytest.mark.django_db
class TestCopilotBookkeepingService:
    """CopilotBookkeepingService 单元测试"""

    def setup_method(self):
        cache.clear()

    # ------------------------------------------------------------------
    # 基础常量与暂存区键
    # ------------------------------------------------------------------
    def test_source_constants_and_staging_key(self):
        assert CopilotBookkeepingService.SOURCE == 'copilot'
        assert CopilotBookkeepingService.SOURCE_LABEL == 'Copilot 记账'
        assert CopilotBookkeepingService.staging_key(7) == 'copilot:7'
        assert ParseReviewService._get_cache_key(
            CopilotBookkeepingService.staging_key(7)
        ) == 'parse_result:copilot:7'

    def test_source_ref_shape(self):
        assert CopilotBookkeepingService.source_ref('u1') == {
            'source': 'copilot',
            'file_id': None,
            'uuid': 'u1',
        }

    # ------------------------------------------------------------------
    # 条目文本与 signs
    # ------------------------------------------------------------------
    def test_expense_entry_text_and_signs(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [_entry()])

        assert result['ok'] is True
        assert result['errors'] == []
        assert len(result['created']) == 1
        created = result['created'][0]
        assert created['type'] == 'expense'
        assert created['date'] == '2025-01-20'
        assert created['amount'] == '35.00'
        assert created['currency'] == 'CNY'
        assert created['account'] == EXPENSE_ACCOUNT
        assert created['counterparty_account'] == ASSET_ACCOUNT
        assert created['summary'] == '支出 2025-01-20 35.00 CNY 午餐'

        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert created['uuid'] == entry['uuid']
        formatted = entry['formatted']
        assert formatted.startswith('2025-01-20 * "食堂" "午餐"')
        # 支出账户为正，资金账户为负
        assert f'    {EXPENSE_ACCOUNT} 35.00 CNY' in formatted
        assert f'    {ASSET_ACCOUNT} -35.00 CNY' in formatted
        # 元数据与账单解析条目一致
        assert '    time: "' in formatted
        assert f'    uuid: "{entry["uuid"]}"' in formatted
        assert '    status: "Copilot - 已记录"' in formatted
        assert entry['edited_formatted'] == formatted
        assert BeancountValidator.validate_single_entry(formatted)[0] is True

    def test_income_entry_text_and_signs(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(type='income', amount=500.0, narration='工资', payee='公司'),
        ])

        assert result['ok'] is True
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        formatted = entry['formatted']
        # 收入账户为负，资金账户为正
        assert f'    {INCOME_ACCOUNT} -500.00 CNY' in formatted
        assert f'    {ASSET_ACCOUNT} 500.00 CNY' in formatted
        assert EXPENSE_ACCOUNT not in formatted
        assert entry['original_row']['transaction_type'] == '收入'
        assert BeancountValidator.validate_single_entry(formatted)[0] is True

    def test_transfer_entry_text_and_signs(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(type='transfer', amount=100.0, narration='充值', payee='本人'),
        ])

        assert result['ok'] is True
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        formatted = entry['formatted']
        # 转出为负、转入为正
        assert f'    {ASSET_ACCOUNT} -100.00 CNY' in formatted
        assert f'    {ASSET_WALLET} 100.00 CNY' in formatted
        assert 'Expenses:' not in formatted
        assert 'Income:' not in formatted
        assert entry['original_row']['transaction_type'] == '/'
        assert entry['original_row']['payment_method'] == ASSET_WALLET
        assert BeancountValidator.validate_single_entry(formatted)[0] is True

    # ------------------------------------------------------------------
    # 条目结构与去重字段
    # ------------------------------------------------------------------
    def test_tag_details_and_original_row_and_dedup_fields(self, accounts, tag):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(tags=['#Category/Food']),
        ])
        assert result['ok'] is True

        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert '#Category/Food' in entry['formatted'].split('\n')[0]
        assert entry['tag_details'] == [
            {'path': TAG_PATH, 'sources': [{'type': 'manual'}]}
        ]
        assert entry['tag_overrides'] == {'removed_paths': [], 'added_paths': []}
        assert entry['selected_expense_key'] is None
        assert entry['expense_candidates_with_score'] == []
        assert entry['installment_role'] is None
        assert entry['installment_period'] is None

        original_row = entry['original_row']
        assert original_row['bill_identifier'] == 'copilot'
        assert original_row['transaction_type'] == '支出'
        assert original_row['counterparty'] == '食堂'
        assert original_row['commodity'] == '午餐'
        assert original_row['amount'] == '35.00'
        assert original_row['payment_method'] == ASSET_ACCOUNT
        assert original_row['uuid'] == entry['uuid']
        assert original_row['transaction_time'].startswith('2025-01-20 ')

        # 供 EntryDedupService 取值的合成字段
        assert entry['date'] == '2025-01-20'
        assert entry['amount'] == '35.00'
        assert entry['transaction_type'] == '支出'
        assert entry['counterparty'] == '食堂'
        assert entry['commodity'] == '午餐'

    def test_tags_accept_without_hash_and_dedupe(self, accounts, tag):
        """标签允许带 / 不带 #，重复标签只保留一次。"""
        CopilotBookkeepingService.create_entries(accounts, [
            _entry(tags=['Category/Food', '#Category/Food']),
        ])
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert entry['tag_details'] == [
            {'path': TAG_PATH, 'sources': [{'type': 'manual'}]}
        ]

    def test_payee_defaults_to_narration(self, accounts):
        CopilotBookkeepingService.create_entries(accounts, [
            _entry(payee=None, narration='打车'),
        ])
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert entry['original_row']['counterparty'] == '打车'
        assert entry['formatted'].startswith('2025-01-20 * "打车" "打车"')

    # ------------------------------------------------------------------
    # 暂存区创建与追加
    # ------------------------------------------------------------------
    def test_staging_created_and_append_keeps_expiry(self, accounts):
        CopilotBookkeepingService.create_entries(accounts, [_entry(narration='第一笔')])

        assert CopilotBookkeepingService.has_staging(accounts.id) is True
        data1 = CopilotBookkeepingService.get_staging_data(accounts.id)
        assert len(data1['formatted_data']) == 1
        assert data1['review_expires_at'] - data1['created_at'] == pytest.approx(
            ParseReviewService.REVIEW_DEADLINE_SECONDS
        )
        created_at = data1['created_at']
        expires_at = data1['review_expires_at']

        CopilotBookkeepingService.create_entries(accounts, [_entry(narration='第二笔')])

        data2 = CopilotBookkeepingService.get_staging_data(accounts.id)
        assert [e['commodity'] for e in data2['formatted_data']] == ['第一笔', '第二笔']
        # 追加不延长审核截止时间
        assert data2['created_at'] == created_at
        assert data2['review_expires_at'] == expires_at
        assert CopilotBookkeepingService.expires_at(accounts.id) == expires_at

    def test_get_entry_remove_entries_and_clear(self, accounts):
        CopilotBookkeepingService.create_entries(accounts, [
            _entry(narration='A'),
            _entry(narration='B'),
        ])

        entries = CopilotBookkeepingService.list_entries(accounts.id)
        assert len(entries) == 2
        assert entries[0]['source'] == 'copilot'
        assert entries[0]['file_id'] is None
        assert entries[0]['file_name'] == 'Copilot 记账'

        target_uuid = entries[0]['uuid']
        assert CopilotBookkeepingService.get_entry(accounts.id, target_uuid)['uuid'] == target_uuid
        assert CopilotBookkeepingService.get_entry(accounts.id, 'missing') is None

        assert CopilotBookkeepingService.remove_entries(accounts.id, [target_uuid]) is True
        remaining = CopilotBookkeepingService.list_entries(accounts.id)
        assert [e['uuid'] for e in remaining] == [entries[1]['uuid']]

        assert CopilotBookkeepingService.clear(accounts.id) is True
        assert CopilotBookkeepingService.has_staging(accounts.id) is False
        assert CopilotBookkeepingService.list_entries(accounts.id) == []

    # ------------------------------------------------------------------
    # 入队与待办
    # ------------------------------------------------------------------
    def test_enqueue_ref_and_task_activated(self, accounts, entry_review_task_inactive):
        CopilotBookkeepingService.create_entries(accounts, [_entry()])

        entry_uuid = CopilotBookkeepingService.list_entries(accounts.id)[0]['uuid']
        expected_refs = [{'source': 'copilot', 'file_id': None, 'uuid': entry_uuid}]
        assert EntryReviewQueueService._get_refs(accounts.id) == expected_refs
        assert EntryReviewQueueService.list_refs(accounts.id) == expected_refs

        entry_review_task_inactive.refresh_from_db()
        assert entry_review_task_inactive.status == 'pending'
        assert ScheduledTask.objects.filter(
            task_type='entry_review',
            object_id=accounts.id,
        ).count() == 1

    def test_duplicate_entry_skipped(self, accounts, tag):
        CopilotBookkeepingService.create_entries(accounts, [_entry()])

        result = CopilotBookkeepingService.create_entries(accounts, [_entry()])

        assert result['ok'] is False
        assert result['created'] == []
        assert len(result['duplicates']) == 1
        duplicate = result['duplicates'][0]
        assert duplicate['type'] == 'expense'
        assert duplicate['date'] == '2025-01-20'
        assert duplicate['amount'] == '35.00'
        assert duplicate['narration'] == '午餐'
        assert duplicate['reason'] == '与待审核队列中已有条目重复'
        assert result['pending_total'] == 1

        # 暂存区与队列都未新增
        assert len(CopilotBookkeepingService.list_entries(accounts.id)) == 1
        assert len(EntryReviewQueueService.list_refs(accounts.id)) == 1

    # ------------------------------------------------------------------
    # 校验失败逐条跳过
    # ------------------------------------------------------------------
    def test_invalid_entries_reported_with_one_based_index(self, accounts, tag):
        entries = [
            _entry(),                                            # 1 合法
            _entry(type='refund'),                               # 2 type 非法
            _entry(date='2025/01/20'),                           # 3 date 格式非法
            _entry(amount=-5),                                   # 4 amount 非正
            _entry(narration='   '),                             # 5 narration 为空
            _entry(account='Expenses:NotExist'),                 # 6 账户不存在
            _entry(account=INCOME_ACCOUNT),                      # 7 账户类型不匹配
            _entry(payment_account='Assets:NotExist'),           # 8 资金账户不存在
            _entry(currency='USD'),                              # 9 非默认币种
            _entry(tags=['#NotExist']),                          # 10 标签不存在
        ]

        result = CopilotBookkeepingService.create_entries(accounts, entries)

        assert result['ok'] is True
        assert len(result['created']) == 1
        errors = {e['index']: e['error'] for e in result['errors']}
        assert set(errors) == {2, 3, 4, 5, 6, 7, 8, 9, 10}
        assert errors[2] == 'type 必须是 expense / income / transfer 之一'
        assert errors[3] == 'date 必须是 YYYY-MM-DD 格式'
        assert errors[4] == 'amount 必须大于 0'
        assert errors[5] == 'narration 不能为空'
        assert errors[6] == _ACCOUNT_MISSING_MESSAGE
        assert errors[7] == 'account 必须是 Expenses:* 账户'
        assert errors[8] == _ACCOUNT_MISSING_MESSAGE
        assert errors[9] == '暂不支持非默认币种，当前仅支持 CNY'
        assert errors[10] == '标签不存在于用户标签目录: NotExist'

        # 仅 1 条合法条目写入暂存区
        assert len(CopilotBookkeepingService.list_entries(accounts.id)) == 1

    def test_transfer_same_account_or_non_list_tags_rejected(self, accounts, tag):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(type='transfer', to_account=ASSET_ACCOUNT),
            _entry(tags='Category/Food'),
        ])
        errors = {e['index']: e['error'] for e in result['errors']}
        assert errors[1] == 'transfer 的 from_account 与 to_account 不能相同'
        assert errors[2] == 'tags 必须是数组'

    def test_invalid_calendar_date_rejected(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(date='2025-13-40'),
        ])
        assert result['errors'] == [{'index': 1, 'error': 'date 不是有效日期: 2025-13-40'}]

    def test_transfer_requires_asset_accounts(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(type='transfer', from_account=EXPENSE_ACCOUNT, to_account=ASSET_WALLET),
            _entry(type='transfer', from_account=ASSET_ACCOUNT, to_account='Assets:NotExist'),
        ])
        errors = {e['index']: e['error'] for e in result['errors']}
        assert errors[1] == 'transfer 的 from_account / to_account 必须是 Assets:* 账户'
        assert errors[2] == _ACCOUNT_MISSING_MESSAGE

    def test_income_requires_income_account_and_existing_payment_account(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(type='income', account=EXPENSE_ACCOUNT),
            _entry(type='income', payment_account='Income:NotExist'),
        ])
        errors = {e['index']: e['error'] for e in result['errors']}
        assert errors[1] == 'account 必须是 Income:* 账户'
        assert errors[2] == _ACCOUNT_MISSING_MESSAGE

    def test_disabled_account_not_accepted(self, accounts):
        Account.objects.create(account='Expenses:Old', owner=accounts, enable=False)
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(account='Expenses:Old'),
        ])
        assert result['errors'] == [{'index': 1, 'error': _ACCOUNT_MISSING_MESSAGE}]

    def test_liability_payment_account_accepted(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(payment_account=LIABILITY_ACCOUNT),
        ])
        assert result['ok'] is True
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert f'    {LIABILITY_ACCOUNT} -35.00 CNY' in entry['formatted']

    def test_non_asset_payment_account_accepted(self, accounts):
        result = CopilotBookkeepingService.create_entries(accounts, [
            _entry(payment_account=EXPENSE_ACCOUNT),
        ])
        assert result['ok'] is True
        entry = CopilotBookkeepingService.list_entries(accounts.id)[0]
        assert f'    {EXPENSE_ACCOUNT} -35.00 CNY' in entry['formatted']

    # ------------------------------------------------------------------
    # 条数上限与空入参
    # ------------------------------------------------------------------
    def test_exceeding_max_entries_rejected(self, accounts):
        with override_settings(COPILOT_BOOKKEEPING_MAX_ENTRIES=2):
            result = CopilotBookkeepingService.create_entries(accounts, [
                _entry(narration='A'),
                _entry(narration='B'),
                _entry(narration='C'),
            ])

        assert result['ok'] is False
        assert result['created'] == []
        assert result['errors'] == [
            {'index': None, 'error': '单次最多提交 2 笔交易，当前 3 笔'}
        ]
        assert CopilotBookkeepingService.has_staging(accounts.id) is False
        assert EntryReviewQueueService.is_empty(accounts.id) is True

    def test_empty_or_non_list_entries_rejected(self, accounts):
        for payload in ([], None, 'not-a-list'):
            result = CopilotBookkeepingService.create_entries(accounts, payload)
            assert result['ok'] is False
            assert result['errors'] == [{'index': None, 'error': 'entries 必须是非空数组'}]
        assert CopilotBookkeepingService.has_staging(accounts.id) is False
