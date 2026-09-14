"""
EntryDedupService 条目入队前去重服务单元测试
"""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from project.apps.translate.services.entry_dedup_service import EntryDedupService


def _make_entry(
    uuid='',
    date='2025-01-20',
    amount=100.00,
    order_uuid='',
    tx_type='支出',
    counterparty='商户',
    commodity='商品',
    transaction_time=None,
):
    """构造解析条目字典（结构与真实缓存条目一致）"""
    original_row = {
        'transaction_type': tx_type,
        'counterparty': counterparty,
        'commodity': commodity,
        'amount': amount,
    }
    if order_uuid:
        original_row['uuid'] = order_uuid
    if transaction_time is not None:
        original_row['transaction_time'] = transaction_time
    return {
        'uuid': uuid,
        'date': date,
        'amount': amount,
        'original_row': original_row,
    }


def _make_provider(
    configured=True,
    api_key='test-key',
    base_url='https://api.example.com',
    model='test-model',
):
    """构造 LLM 供给对象（鸭子类型，仅需实现用到的属性）"""
    return MagicMock(
        configured=configured,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def _mock_openai_client(content):
    """构造 openai.OpenAI 客户端 mock，返回指定 content 的响应"""
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
    return client


_RESOLVE_PATH = 'project.apps.assistant.services.api_key_resolver.resolve_llm_provider'


@pytest.fixture
def dedup_user(db):
    """创建去重测试用户"""
    return get_user_model().objects.create_user(
        username='dedupuser',
        password='testpass123',
    )


class TestEntryDedupService:
    """EntryDedupService 单元测试"""

    # ------------------------------------------------------------------
    # 开关与取值辅助
    # ------------------------------------------------------------------
    def test_is_enabled_true(self):
        """去重开关开启"""
        with override_settings(ENTRY_REVIEW_DEDUP_ENABLED=True):
            assert EntryDedupService.is_enabled() is True

    def test_is_enabled_false(self):
        """去重开关关闭"""
        with override_settings(ENTRY_REVIEW_DEDUP_ENABLED=False):
            assert EntryDedupService.is_enabled() is False

    def test_entry_date_prefers_transaction_time(self):
        """日期优先取原始行 transaction_time 前 10 位"""
        entry = _make_entry(date='1999-01-01', transaction_time='2025-01-20 09:30:00')
        assert EntryDedupService.entry_date(entry) == '2025-01-20'

    def test_entry_date_falls_back_to_date(self):
        """无 transaction_time 时退化到 date"""
        assert EntryDedupService.entry_date(_make_entry(date='2025-03-05')) == '2025-03-05'
        assert EntryDedupService.entry_date({}) is None

    def test_entry_amount_prefers_original_row(self):
        """金额优先取原始行 amount"""
        entry = {'amount': 5, 'original_row': {'amount': 100}}
        assert EntryDedupService.entry_amount(entry) == 100.0

    def test_entry_amount_fallback_and_invalid(self):
        """原始行无 amount 时退化到条目 amount，非法值返回 None"""
        assert EntryDedupService.entry_amount({'amount': '88.5', 'original_row': {}}) == 88.5
        assert EntryDedupService.entry_amount({'amount': 'abc', 'original_row': {}}) is None
        assert EntryDedupService.entry_amount({}) is None

    def test_entry_field_helpers(self):
        """单号/收支/对方/品名/文件标识取值"""
        entry = _make_entry(
            order_uuid='ORD-1',
            tx_type='收入',
            counterparty='对方A',
            commodity='商品B',
            date='2025-01-20',
            amount=12.0,
        )
        entry['file_name'] = '账单.csv'
        assert EntryDedupService.entry_order_uuid(entry) == 'ORD-1'
        assert EntryDedupService.entry_tx_type(entry) == '收入'
        assert EntryDedupService.entry_counterparty(entry) == '对方A'
        assert EntryDedupService.entry_commodity(entry) == '商品B'
        assert EntryDedupService.entry_file_label(entry) == '账单.csv'
        assert EntryDedupService.entry_order_uuid({}) == ''
        assert EntryDedupService.entry_file_label({}) == ''

    # ------------------------------------------------------------------
    # 确定性判定
    # ------------------------------------------------------------------
    def test_is_fast_duplicate_same_order_uuid_and_date(self):
        """单号相同且日期相同判为快速重复"""
        a = _make_entry(order_uuid='ORD-1', date='2025-01-20')
        b = _make_entry(order_uuid='ORD-1', date='2025-01-20')
        assert EntryDedupService._is_fast_duplicate(a, b) is True

    def test_is_fast_duplicate_requires_same_nonempty_uuid_and_date(self):
        """单号为空/不同，或日期不同，均不判为快速重复"""
        base = _make_entry(order_uuid='ORD-1', date='2025-01-20')
        assert EntryDedupService._is_fast_duplicate(
            _make_entry(order_uuid='', date='2025-01-20'), base
        ) is False
        assert EntryDedupService._is_fast_duplicate(
            _make_entry(order_uuid='ORD-2', date='2025-01-20'), base
        ) is False
        assert EntryDedupService._is_fast_duplicate(
            _make_entry(order_uuid='ORD-1', date='2025-01-21'), base
        ) is False

    def test_fast_duplicate_does_not_call_llm(self):
        """快速判定命中时不触发 LLM 判定"""
        new = [_make_entry(uuid='n1', order_uuid='ORD-1', date='2025-01-20', amount=100.0)]
        existing = [_make_entry(uuid='e1', order_uuid='ORD-1', date='2025-01-20', amount=100.0)]
        with patch.object(EntryDedupService, '_llm_judge_pairs') as mock_judge:
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        mock_judge.assert_not_called()
        assert kept == []
        assert duplicates == new

    def test_is_candidate_within_tolerance_boundary(self):
        """同日期且金额差在容差内（含边界）为候选"""
        a = _make_entry(date='2025-01-20', amount=100.0)
        b = _make_entry(date='2025-01-20', amount=101.0)
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.0):
            assert EntryDedupService._is_candidate(a, b) is True
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=0.5):
            assert EntryDedupService._is_candidate(a, b) is False

    def test_is_candidate_requires_same_date_and_amount(self):
        """日期不同 / 缺金额均不为候选"""
        a = _make_entry(date='2025-01-20', amount=100.0)
        assert EntryDedupService._is_candidate(
            a, _make_entry(date='2025-01-21', amount=100.0)
        ) is False
        b = {'date': '2025-01-20', 'original_row': {}}
        assert EntryDedupService._is_candidate(a, b) is False

    def test_is_exact_duplicate_all_equal(self):
        """五个字段全等判为精确重复"""
        a = _make_entry(
            date='2025-01-20', amount=100.0, tx_type='支出', counterparty='A', commodity='B'
        )
        b = _make_entry(
            date='2025-01-20', amount=100.0, tx_type='支出', counterparty='A', commodity='B'
        )
        assert EntryDedupService._is_exact_duplicate(a, b) is True

    def test_is_exact_duplicate_any_field_differs(self):
        """任一关键字段不同即不为精确重复"""
        a = _make_entry(
            date='2025-01-20', amount=100.0, tx_type='支出', counterparty='A', commodity='B'
        )
        assert EntryDedupService._is_exact_duplicate(
            a, _make_entry(date='2025-01-20', amount=100.0, tx_type='支出', counterparty='C', commodity='B')
        ) is False
        assert EntryDedupService._is_exact_duplicate(
            a, _make_entry(date='2025-01-20', amount=101.0, tx_type='支出', counterparty='A', commodity='B')
        ) is False
        assert EntryDedupService._is_exact_duplicate(
            a, _make_entry(date='2025-01-21', amount=100.0, tx_type='支出', counterparty='A', commodity='B')
        ) is False

    # ------------------------------------------------------------------
    # LLM 返回解析
    # ------------------------------------------------------------------
    def test_parse_verdicts_plain_json(self):
        assert EntryDedupService._parse_verdicts('[true, false]', 2) == [True, False]

    def test_parse_verdicts_json_code_block(self):
        assert EntryDedupService._parse_verdicts('```json\n[true, false]\n```', 2) == [True, False]

    def test_parse_verdicts_with_surrounding_text(self):
        assert EntryDedupService._parse_verdicts('判定结果如下：[true, false]', 2) == [True, False]

    def test_parse_verdicts_int_and_string_items(self):
        """容忍 1/0 与 是/重复 等字符串布尔"""
        assert EntryDedupService._parse_verdicts('[1, 0]', 2) == [True, False]
        assert EntryDedupService._parse_verdicts('["是", "重复"]', 2) == [True, True]
        assert EntryDedupService._parse_verdicts('["yes", "no"]', 2) == [True, False]

    def test_parse_verdicts_invalid_returns_none(self):
        """空串 / 长度不符 / 非 JSON / 非法元素均返回 None"""
        assert EntryDedupService._parse_verdicts('', 2) is None
        assert EntryDedupService._parse_verdicts('[true]', 2) is None
        assert EntryDedupService._parse_verdicts('不是 json', 1) is None
        assert EntryDedupService._parse_verdicts('[true, {"a": 1}]', 2) is None

    # ------------------------------------------------------------------
    # LLM 判定
    # ------------------------------------------------------------------
    def test_llm_judge_pairs_success(self):
        """正常调用 LLM 并解析布尔数组"""
        provider = _make_provider()
        pair = (
            _make_entry(date='2025-01-20', amount=100.0),
            _make_entry(date='2025-01-20', amount=100.5),
        )
        client = _mock_openai_client('[true, false]')
        with patch(_RESOLVE_PATH, return_value=provider), \
                patch('openai.OpenAI', return_value=client) as mock_openai:
            verdicts = EntryDedupService._llm_judge_pairs(MagicMock(), [pair, pair])
        assert verdicts == [True, False]
        kwargs = mock_openai.call_args.kwargs
        assert kwargs['api_key'] == provider.api_key
        assert kwargs['base_url'] == provider.base_url
        assert 'timeout' in kwargs

    def test_llm_judge_pairs_empty_pairs(self):
        """无候选对时不调用 LLM"""
        assert EntryDedupService._llm_judge_pairs(MagicMock(), []) is None

    def test_llm_judge_pairs_unconfigured_returns_none(self):
        """供给未配置时返回 None"""
        pair = (_make_entry(), _make_entry())
        with patch(_RESOLVE_PATH, return_value=_make_provider(configured=False)):
            assert EntryDedupService._llm_judge_pairs(MagicMock(), [pair]) is None

    def test_llm_judge_pairs_resolver_exception_returns_none(self):
        """解析供给抛异常时返回 None（不抛出）"""
        pair = (_make_entry(), _make_entry())
        with patch(_RESOLVE_PATH, side_effect=RuntimeError('resolver down')):
            assert EntryDedupService._llm_judge_pairs(MagicMock(), [pair]) is None

    def test_llm_judge_pairs_call_exception_returns_none(self):
        """LLM 调用超时/异常时返回 None（不抛出）"""
        pair = (_make_entry(), _make_entry())
        client = MagicMock()
        client.chat.completions.create.side_effect = TimeoutError('timeout')
        with patch(_RESOLVE_PATH, return_value=_make_provider()), \
                patch('openai.OpenAI', return_value=client):
            assert EntryDedupService._llm_judge_pairs(MagicMock(), [pair]) is None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def test_dedup_llm_marks_duplicate(self):
        """候选对交由 LLM 判定，命中者计入 duplicates"""
        new = [
            _make_entry(uuid='n1', date='2025-01-20', amount=100.0, counterparty='A'),
            _make_entry(uuid='n2', date='2025-01-20', amount=100.5, counterparty='A'),
        ]
        existing = [_make_entry(uuid='e1', date='2025-01-20', amount=100.6, counterparty='A')]
        client = _mock_openai_client('[false, true]')
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.0), \
                patch(_RESOLVE_PATH, return_value=_make_provider()), \
                patch('openai.OpenAI', return_value=client):
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        assert [e['uuid'] for e in kept] == ['n1']
        assert [e['uuid'] for e in duplicates] == ['n2']

    def test_dedup_fallback_exact_match_when_llm_unavailable(self):
        """LLM 未配置时回退精确匹配：全等剔除、近似保留、无候选取保留"""
        new = [
            _make_entry(uuid='n1', date='2025-01-20', amount=100.0,
                        tx_type='支出', counterparty='A', commodity='B'),
            _make_entry(uuid='n2', date='2025-01-20', amount=100.5,
                        tx_type='支出', counterparty='A', commodity='B'),
            _make_entry(uuid='n3', date='2025-02-01', amount=999.0,
                        tx_type='支出', counterparty='Z', commodity='C'),
        ]
        existing = [_make_entry(uuid='e1', date='2025-01-20', amount=100.0,
                                tx_type='支出', counterparty='A', commodity='B')]
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.0), \
                patch(_RESOLVE_PATH, return_value=_make_provider(configured=False)):
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        assert [e['uuid'] for e in kept] == ['n2', 'n3']
        assert [e['uuid'] for e in duplicates] == ['n1']

    def test_dedup_fallback_when_llm_raises(self):
        """LLM 调用抛异常时回退精确匹配且不抛错"""
        new = [_make_entry(uuid='n1', date='2025-01-20', amount=100.0,
                           tx_type='支出', counterparty='A', commodity='B')]
        existing = [_make_entry(uuid='e1', date='2025-01-20', amount=100.0,
                                tx_type='支出', counterparty='A', commodity='B')]
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.0), \
                patch(_RESOLVE_PATH, return_value=_make_provider()), \
                patch('openai.OpenAI', side_effect=RuntimeError('client error')):
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        assert kept == []
        assert [e['uuid'] for e in duplicates] == ['n1']

    def test_dedup_disabled_skips_everything(self):
        """开关关闭时全部保留，且不触发 LLM"""
        new = [_make_entry(uuid='n1', order_uuid='ORD-1', date='2025-01-20', amount=100.0)]
        existing = [_make_entry(uuid='e1', order_uuid='ORD-1', date='2025-01-20', amount=100.0)]
        with override_settings(ENTRY_REVIEW_DEDUP_ENABLED=False), \
                patch.object(EntryDedupService, '_llm_judge_pairs') as mock_judge:
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        mock_judge.assert_not_called()
        assert kept == new
        assert duplicates == []

    def test_dedup_empty_inputs(self):
        """新条目或已存在条目为空时直接返回"""
        entry = _make_entry(uuid='n1')
        assert EntryDedupService.dedup_new_entries(MagicMock(), [], [entry]) == ([], [])
        assert EntryDedupService.dedup_new_entries(MagicMock(), [entry], []) == ([entry], [])

    def test_dedup_mixed_fast_and_unique_order_preserved(self):
        """快速重复与无关条目混合时，保留/剔除均保持原顺序"""
        new = [
            _make_entry(uuid='n1', order_uuid='ORD-1', date='2025-01-20', amount=100.0),
            _make_entry(uuid='n2', date='2025-03-01', amount=200.0),
            _make_entry(uuid='n3', order_uuid='ORD-9', date='2025-04-01', amount=300.0),
        ]
        existing = [
            _make_entry(uuid='e1', order_uuid='ORD-1', date='2025-01-20', amount=100.0),
            _make_entry(uuid='e3', order_uuid='ORD-9', date='2025-04-01', amount=300.0),
        ]
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=0.0):
            kept, duplicates = EntryDedupService.dedup_new_entries(MagicMock(), new, existing)
        assert [e['uuid'] for e in kept] == ['n2']
        assert [e['uuid'] for e in duplicates] == ['n1', 'n3']

    def test_tolerance_setting_takes_effect(self):
        """容差配置生效"""
        a = _make_entry(date='2025-01-20', amount=100.0)
        b = _make_entry(date='2025-01-20', amount=100.8)
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=0):
            assert EntryDedupService._is_candidate(a, b) is False
        with override_settings(ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.5):
            assert EntryDedupService._is_candidate(a, b) is True

    @pytest.mark.django_db
    def test_dedup_real_user_without_provider_falls_back(self, dedup_user):
        """真实用户且未配置 Provider 时，走回退精确匹配"""
        new = [
            _make_entry(uuid='n1', date='2025-01-20', amount=100.0,
                        tx_type='支出', counterparty='A', commodity='B'),
            _make_entry(uuid='n2', date='2025-02-02', amount=50.0,
                        tx_type='支出', counterparty='C', commodity='D'),
        ]
        existing = [_make_entry(uuid='e1', date='2025-01-20', amount=100.0,
                                tx_type='支出', counterparty='A', commodity='B')]
        with override_settings(
            ASSISTANT_DEEPSEEK_API_KEY='',
            ENTRY_REVIEW_DEDUP_AMOUNT_TOLERANCE=1.0,
            ENTRY_REVIEW_DEDUP_ENABLED=True,
        ):
            kept, duplicates = EntryDedupService.dedup_new_entries(dedup_user, new, existing)
        assert [e['uuid'] for e in kept] == ['n2']
        assert [e['uuid'] for e in duplicates] == ['n1']

    def test_describe_duplicate(self):
        """日志摘要包含关键字段"""
        entry = _make_entry(
            uuid='n1', order_uuid='ORD-1', date='2025-01-20',
            amount=100.0, tx_type='支出', counterparty='A', commodity='B',
        )
        matched = _make_entry(uuid='e1', order_uuid='ORD-1', date='2025-01-20', amount=100.0)
        summary = EntryDedupService.describe_duplicate(entry, matched)
        assert summary['uuid'] == 'n1'
        assert summary['date'] == '2025-01-20'
        assert summary['amount'] == 100.0
        assert summary['order_uuid'] == 'ORD-1'
        assert summary['matched']['uuid'] == 'e1'
