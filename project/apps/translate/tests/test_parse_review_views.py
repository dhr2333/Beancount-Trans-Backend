"""
统一条目审核 API（EntryReview* 视图）测试

统一改造后，审核接口以用户级队列（EntryReviewQueueService）为数据源：
- GET  /api/translate/entry-review/results
- POST /api/translate/entry-review/reparse
- PUT  /api/translate/entry-review/entries/<uuid>/edit
- PATCH /api/translate/entry-review/entries/<uuid>/tags
- PUT  /api/translate/entry-review/preview-sync
- POST /api/translate/entry-review/confirm
- POST /api/translate/entry-review/reparse-all
"""
import time
from unittest.mock import patch, MagicMock

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.translate.services.entry_review_queue_service import EntryReviewQueueService
from project.apps.translate.models import ParseFile
from project.apps.file_manager.models import File


def _make_entry(entry_uuid, formatted=None, **extra):
    """构造一条审核条目（默认带合法账目文本与原始行）。"""
    if formatted is None:
        formatted = (
            '2025-01-20 * "Test" "Transaction"\n'
            '    Expenses:Test  100.00 CNY\n'
            '    Assets:Test  -100.00 CNY\n'
        )
    entry = {
        'uuid': entry_uuid,
        'formatted': formatted,
        'edited_formatted': formatted,
        'selected_expense_key': 'Expenses:Test',
        'expense_candidates_with_score': [{'key': 'Expenses:Test', 'score': 0.9}],
        'original_row': {
            'date': '2025-01-20',
            'transaction_time': '2025-01-20 10:00:00',
            'description': 'Test Transaction',
            'amount': 100.0,
        },
        'tag_details': [],
        'tag_overrides': {'removed_paths': [], 'added_paths': []},
    }
    entry.update(extra)
    return entry


def _save_review(file_id, entries, expires_in=86400):
    """写入解析缓存并返回缓存数据。"""
    data = {
        'file_id': file_id,
        'formatted_data': entries,
        'created_at': time.time(),
        'review_expires_at': time.time() + expires_in,
    }
    ParseReviewService.save_parse_result(file_id, data)
    return data


def _enqueue(user, refs):
    """把条目引用加入用户级审核队列。"""
    EntryReviewQueueService.enqueue(user.id, refs)


def _create_second_parse_file(user, directory, name='test_file2.csv'):
    """为多文件场景创建第二个 ParseFile。"""
    file_obj = File.objects.create(
        name=name,
        directory=directory,
        storage_name=f'storage_{name}',
        size=1024,
        owner=user,
        content_type='text/csv',
    )
    return ParseFile.objects.create(file=file_obj, status='pending_review')


@pytest.mark.django_db
class TestEntryReviewResultsView:
    """GET /api/translate/entry-review/results 测试"""

    def setup_method(self):
        self.client = APIClient()

    def test_get_results_success(self, user, entry_review_task, parse_file):
        """成功返回扁平条目 + file_id/file_name + 整体 review_expires_at"""
        self.client.force_authenticate(user=user)

        data = _save_review(parse_file.file_id, [
            _make_entry('entry-1'),
            _make_entry('entry-2'),
        ])
        _enqueue(user, [
            {'file_id': parse_file.file_id, 'uuid': 'entry-1'},
            {'file_id': parse_file.file_id, 'uuid': 'entry-2'},
        ])

        response = self.client.get('/api/translate/entry-review/results')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['entry_count'] == 2
        entries = response.data['entries']
        assert [e['uuid'] for e in entries] == ['entry-1', 'entry-2']
        for entry in entries:
            assert entry['file_id'] == parse_file.file_id
            assert entry['file_name'] == parse_file.file.name
            # 去除末尾换行符
            assert not entry['formatted'].endswith('\n')
            assert not entry['edited_formatted'].endswith('\n')
        # 整体审核截止时间取队列中最早到期值
        assert response.data['review_expires_at'] == pytest.approx(
            data['review_expires_at']
        )

    def test_get_results_cache_missing_returns_empty(self, user, entry_review_task, parse_file):
        """解析缓存缺失时，队列引用被剔除，返回空结果"""
        self.client.force_authenticate(user=user)

        ParseReviewService.delete_parse_result(parse_file.file_id)
        _enqueue(user, [{'file_id': parse_file.file_id, 'uuid': 'entry-1'}])

        response = self.client.get('/api/translate/entry-review/results')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['entries'] == []
        assert response.data['entry_count'] == 0
        assert response.data['review_expires_at'] is None

    def test_get_results_without_task_still_returns_entries(self, user, parse_file):
        """results 接口不依赖待办状态，仅按队列返回条目（记录真实行为）"""
        self.client.force_authenticate(user=user)

        _save_review(parse_file.file_id, [_make_entry('entry-1')])
        _enqueue(user, [{'file_id': parse_file.file_id, 'uuid': 'entry-1'}])

        response = self.client.get('/api/translate/entry-review/results')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['entry_count'] == 1

    def test_get_results_unauthenticated(self):
        """未认证用户无法访问"""
        response = self.client.get('/api/translate/entry-review/results')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEntryReviewReparseView:
    """POST /api/translate/entry-review/reparse 测试"""

    def setup_method(self):
        self.client = APIClient()

    @patch('project.apps.translate.views.views.single_parse_transaction')
    @patch('project.apps.translate.views.views.FormatData.format_instance')
    @patch('project.apps.translate.views.views.get_user_config')
    def test_reparse_entry_success(self, mock_get_config, mock_format, mock_parse, user, entry_review_task, parse_file, mock_parse_result_data):
        """成功重解析单个条目"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        mock_get_config.return_value = MagicMock()
        mock_parse.return_value = {
            'expense_candidates_with_score': [{'key': 'Expenses:Updated', 'score': 0.95}]
        }
        mock_format.return_value = '2025-01-20 * "Updated" "Transaction"\n    Expenses:Updated  150.00 CNY\n    Assets:Test  -150.00 CNY\n'

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {
                'file_id': parse_file.file_id,
                'entry_uuid': 'entry-1',
                'selected_key': 'Expenses:Updated',
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == 'entry-1'
        assert 'formatted' in response.data
        assert 'edited_formatted' in response.data
        assert response.data['selected_expense_key'] == 'Expenses:Updated'
        assert 'propagated_entries' in response.data

        # 验证缓存已更新
        cached_data = ParseReviewService.get_parse_result(parse_file.file_id)
        updated_entry = next((e for e in cached_data['formatted_data'] if e['uuid'] == 'entry-1'), None)
        assert updated_entry is not None

    def test_reparse_entry_missing_entry_uuid(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """缺少 entry_uuid 参数"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {'file_id': parse_file.file_id, 'selected_key': 'Expenses:Test'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']

    def test_reparse_entry_missing_selected_key(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """缺少 selected_key 参数"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {'file_id': parse_file.file_id, 'entry_uuid': 'entry-1'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']

    def test_reparse_entry_uuid_not_found(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """条目 UUID 不存在"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {
                'file_id': parse_file.file_id,
                'entry_uuid': 'non-existent-uuid',
                'selected_key': 'Expenses:Test',
            },
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '未找到对应的条目' in response.data['error']

    def test_reparse_entry_file_not_found(self, user, entry_review_task):
        """file_id 对应文件不存在"""
        self.client.force_authenticate(user=user)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {'file_id': 999999, 'entry_uuid': 'entry-1', 'selected_key': 'Expenses:Test'},
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == '文件不存在'

    def test_reparse_entry_permission_denied(self, user, other_user, entry_review_task, parse_file, mock_parse_result_data):
        """他人文件无权访问"""
        self.client.force_authenticate(user=other_user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {
                'file_id': parse_file.file_id,
                'entry_uuid': 'entry-1',
                'selected_key': 'Expenses:Test',
            },
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == '无权访问该文件'

    def test_reparse_entry_task_completed(self, user, entry_review_task_completed, parse_file, mock_parse_result_data):
        """待办已完成时拒绝重解析"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {
                'file_id': parse_file.file_id,
                'entry_uuid': 'entry-1',
                'selected_key': 'Expenses:Test',
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == '待办任务已完成或已取消'

    @patch('project.apps.translate.views.views.resolve_refund_peer_for_row', return_value=None)
    @patch('project.apps.translate.views.views.get_user_config')
    @patch('project.apps.translate.views.views.single_parse_transaction')
    def test_reparse_purchase_keeps_installment_siblings(
        self, mock_parse, mock_get_config, _mock_peer, user, entry_review_task, parse_file
    ):
        """审核页改分类只更新 purchase 切片，分期还款行仍是 Payables↔信用卡。"""
        from project.apps.translate.utils import BILL_ALI, FormatConfig

        self.client.force_authenticate(user=user)
        mock_get_config.return_value = FormatConfig()
        order = '2024030122001174561405075488'
        original_row = {
            'transaction_time': '2024-03-01 21:08:08',
            'transaction_category': '家居家装',
            'counterparty': '公牛旗舰店',
            'commodity': '轨道插座',
            'transaction_type': '支出',
            'amount': 444.00,
            'payment_method': '中信银行信用卡分期(6428) 3期',
            'transaction_status': '交易成功',
            'notes': '/',
            'bill_identifier': BILL_ALI,
            'uuid': order,
            'discount': False,
        }
        mock_parse.side_effect = lambda row, *_args, **_kwargs: {
            'date': '2024-03-01',
            'time': '21:08:08',
            'uuid': order,
            'status': 'ALiPay - 交易成功',
            'payee': '公牛旗舰店',
            'note': '轨道插座',
            'tag': '#Project/Decoration',
            'links': [order],
            'balance': None,
            'balance_date': '2024-03-02',
            'expense': 'Expenses:Shopping:Digital',
            'expenditure_sign': '',
            'account': 'Liabilities:CreditCard:Bank:CITIC:C6428',
            'account_sign': '-',
            'amount': '444.00',
            'discount': False,
            'currency': 'CNY',
            'selected_expense_key': '公牛',
            'expense_candidates_with_score': [{'key': '公牛', 'score': 0.99}],
            'tag_details': [{'path': 'Project/Decoration', 'sources': [{'type': 'manual'}]}],
        }
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [
                {
                    'uuid': order,
                    'formatted': 'purchase',
                    'edited_formatted': 'purchase',
                    'selected_expense_key': '公牛',
                    'expense_candidates_with_score': [{'key': '公牛', 'score': 0.99}],
                    'original_row': original_row,
                    'installment_role': 'purchase',
                    'installment_period': 0,
                    'tag_details': [],
                    'tag_overrides': {'removed_paths': [], 'added_paths': []},
                },
                {
                    'uuid': f'{order}--2',
                    'formatted': 'installment-0',
                    'edited_formatted': 'installment-0',
                    'selected_expense_key': None,
                    'expense_candidates_with_score': [],
                    'original_row': original_row,
                    'installment_role': 'installment',
                    'installment_period': 0,
                    'tag_details': [],
                    'tag_overrides': {'removed_paths': [], 'added_paths': []},
                },
            ],
            'created_at': time.time(),
            'review_expires_at': time.time() + 86400,
        })

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {'file_id': parse_file.file_id, 'entry_uuid': order, 'selected_key': '装修'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['selected_expense_key'] == '装修'
        assert 'Liabilities:Payables' in response.data['formatted']
        assert 'Expenses:Shopping:Digital' in response.data['formatted']

        cached = ParseReviewService.get_parse_result(parse_file.file_id)
        purchase = next(e for e in cached['formatted_data'] if e['uuid'] == order)
        installment = next(e for e in cached['formatted_data'] if e['uuid'] == f'{order}--2')
        assert purchase['selected_expense_key'] == '装修'
        assert 'Liabilities:Payables' in purchase['formatted']
        assert installment['selected_expense_key'] is None
        assert 'Liabilities:Payables' in installment['formatted']
        assert 'Liabilities:CreditCard:Bank:CITIC:C6428' in installment['formatted']
        assert 'Expenses:Shopping:Digital' not in installment['formatted']

    @patch('project.apps.translate.views.views._propagate_mapping_to_batch')
    @patch('project.apps.translate.views.views._reparse_review_entry')
    def test_reparse_includes_propagated_entries(
        self,
        mock_reparse,
        mock_propagate,
        user,
        entry_review_task,
        parse_file,
    ):
        self.client.force_authenticate(user=user)
        mock_reparse.return_value = {
            'uuid': 'entry-1',
            'formatted': 'formatted-1',
            'edited_formatted': 'formatted-1',
            'selected_expense_key': '商店',
            'expense_candidates_with_score': [{'key': '商店', 'score': 1.0}],
            'tag_details': [],
            'tag_overrides': {'removed_paths': [], 'added_paths': []},
        }
        mock_propagate.return_value = [{
            'uuid': 'entry-2',
            'formatted': 'formatted-2',
            'edited_formatted': 'formatted-2',
            'selected_expense_key': '商店',
            'expense_candidates_with_score': [{'key': '商店', 'score': 1.0}],
            'tag_details': [],
            'tag_overrides': {'removed_paths': [], 'added_paths': []},
        }]
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [{
                'uuid': 'entry-1',
                'formatted': 'old',
                'edited_formatted': 'old',
                'original_row': {'counterparty': '商店', 'commodity': '商品A'},
            }],
            'created_at': time.time(),
            'review_expires_at': time.time() + 86400,
        })

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {'file_id': parse_file.file_id, 'entry_uuid': 'entry-1', 'selected_key': '商店'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['propagated_entries']) == 1
        assert response.data['propagated_entries'][0]['uuid'] == 'entry-2'

    @patch('project.apps.translate.views.views._propagate_mapping_to_batch')
    @patch('project.apps.translate.views.views._reparse_review_entry')
    def test_reparse_asset_mapping_type(
        self,
        mock_reparse,
        mock_propagate,
        user,
        entry_review_task,
        parse_file,
    ):
        self.client.force_authenticate(user=user)
        mock_reparse.return_value = {
            'uuid': 'neutral-1',
            'formatted': 'formatted-neutral',
            'edited_formatted': 'formatted-neutral',
            'selected_expense_key': None,
            'expense_candidates_with_score': [],
            'tag_details': [],
            'tag_overrides': {'removed_paths': [], 'added_paths': []},
        }
        mock_propagate.return_value = []
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [{
                'uuid': 'neutral-1',
                'formatted': 'old',
                'edited_formatted': 'old',
                'selected_expense_key': '',
                'original_row': {
                    'transaction_type': '/',
                    'payment_method': '中国银行储蓄卡(0814)',
                    'counterparty': '/',
                    'commodity': '转账',
                },
            }],
            'created_at': time.time(),
            'review_expires_at': time.time() + 86400,
        })

        response = self.client.post(
            '/api/translate/entry-review/reparse',
            {
                'file_id': parse_file.file_id,
                'entry_uuid': 'neutral-1',
                'selected_key': '0814',
                'mapping_type': 'asset',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        mock_reparse.assert_called_once()
        assert mock_reparse.call_args.kwargs['mapping_type'] == 'asset'
        assert mock_reparse.call_args.kwargs['selected_key'] == '0814'
        mock_propagate.assert_called_once()
        assert mock_propagate.call_args.kwargs['mapping_type'] == 'asset'
        assert mock_propagate.call_args.kwargs['mapping_key'] == '0814'


@pytest.mark.django_db
class TestEntryReviewPreviewSyncView:
    """PUT /api/translate/entry-review/preview-sync 测试"""

    def setup_method(self):
        self.client = APIClient()

    def test_preview_sync_removes_deleted_entry(
        self, user, entry_review_task, parse_file, mock_parse_result_data
    ):
        self.client.force_authenticate(user=user)
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        updated = (
            '2025-01-20 * "Updated" "Transaction 1"\n'
            '    Expenses:Test  100.00 CNY\n'
            '    Assets:Test  -100.00 CNY'
        )
        response = self.client.put(
            '/api/translate/entry-review/preview-sync',
            {
                'file_id': parse_file.file_id,
                'entries': [
                    {'uuid': 'entry-1', 'edited_formatted': updated},
                ],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['removed_count'] == 1
        assert len(response.data['formatted_data']) == 1
        assert response.data['formatted_data'][0]['uuid'] == 'entry-1'
        assert response.data['formatted_data'][0]['edited_formatted'] == updated

        final = ParseReviewService.get_final_result(parse_file.file_id)
        assert len(final) == 1

    def test_preview_sync_unknown_uuid(self, user, entry_review_task, parse_file, mock_parse_result_data):
        self.client.force_authenticate(user=user)
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.put(
            '/api/translate/entry-review/preview-sync',
            {
                'file_id': parse_file.file_id,
                'entries': [{'uuid': 'missing', 'edited_formatted': 'test'}],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_sync_permission_denied(self, user, other_user, entry_review_task, parse_file, mock_parse_result_data):
        self.client.force_authenticate(user=other_user)
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.put(
            '/api/translate/entry-review/preview-sync',
            {
                'file_id': parse_file.file_id,
                'entries': [{'uuid': 'entry-1', 'edited_formatted': 'test'}],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == '无权访问该文件'


@pytest.mark.django_db
class TestEntryReviewEditView:
    """PUT /api/translate/entry-review/entries/<uuid>/edit 测试"""

    def setup_method(self):
        self.client = APIClient()

    def test_update_entry_edit_success(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """成功更新编辑内容"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        new_edited_formatted = '2025-01-20 * "Edited" "Transaction"\n    Expenses:Edited  150.00 CNY\n    Assets:Test  -150.00 CNY\n'

        response = self.client.put(
            '/api/translate/entry-review/entries/entry-1/edit',
            {
                'file_id': parse_file.file_id,
                'edited_formatted': new_edited_formatted,
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == 'entry-1'
        assert response.data['edited_formatted'] == new_edited_formatted

        # 验证缓存已更新
        cached_data = ParseReviewService.get_parse_result(parse_file.file_id)
        updated_entry = next((e for e in cached_data['formatted_data'] if e['uuid'] == 'entry-1'), None)
        assert updated_entry['edited_formatted'] == new_edited_formatted

    def test_update_entry_edit_missing_params(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """缺少 edited_formatted 参数"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.put(
            '/api/translate/entry-review/entries/entry-1/edit',
            {'file_id': parse_file.file_id},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']

    def test_update_entry_edit_validation_warning(self, user, entry_review_task, parse_file, mock_parse_result_data):
        """编辑保存后单条校验失败时返回 validation_warning（不阻断保存）"""
        self.client.force_authenticate(user=user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        invalid_edited = 'invalid beancount syntax'
        response = self.client.put(
            '/api/translate/entry-review/entries/entry-1/edit',
            {'file_id': parse_file.file_id, 'edited_formatted': invalid_edited},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == 'entry-1'
        assert response.data['edited_formatted'] == invalid_edited
        assert 'validation_warning' in response.data
        assert response.data['validation_warning']

    def test_update_entry_edit_permission_denied(self, user, other_user, entry_review_task, parse_file, mock_parse_result_data):
        """他人文件无权编辑"""
        self.client.force_authenticate(user=other_user)

        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)

        response = self.client.put(
            '/api/translate/entry-review/entries/entry-1/edit',
            {'file_id': parse_file.file_id, 'edited_formatted': 'x'},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == '无权访问该文件'


@pytest.mark.django_db
class TestEntryReviewTagsView:
    """PATCH /api/translate/entry-review/entries/<uuid>/tags 测试"""

    def setup_method(self):
        self.client = APIClient()

    def test_patch_remove_tag(self, user, entry_review_task, parse_file):
        self.client.force_authenticate(user=user)
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [{
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Payee" "Note" #RemoveMe\n    Expenses:Test  1 CNY\n',
                'edited_formatted': '2025-01-20 * "Payee" "Note" #RemoveMe\n    Expenses:Test  1 CNY\n',
                'tag_details': [{'path': 'RemoveMe', 'sources': [{'type': 'manual'}]}],
                'tag_overrides': ParseReviewService.default_tag_overrides(),
            }],
            'created_at': time.time(),
            'review_expires_at': time.time() + 86400,
        })

        response = self.client.patch(
            '/api/translate/entry-review/entries/entry-1/tags',
            {'file_id': parse_file.file_id, 'action': 'remove', 'tag_path': 'RemoveMe'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert '#RemoveMe' not in response.data['edited_formatted']
        assert 'RemoveMe' in response.data['tag_overrides']['removed_paths']

    def test_patch_tags_permission_denied(self, user, other_user, entry_review_task, parse_file):
        self.client.force_authenticate(user=other_user)

        response = self.client.patch(
            '/api/translate/entry-review/entries/entry-1/tags',
            {'file_id': parse_file.file_id, 'action': 'remove', 'tag_path': 'RemoveMe'},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == '无权访问该文件'


@pytest.mark.django_db
class TestEntryReviewConfirmView:
    """POST /api/translate/entry-review/confirm 测试"""

    def setup_method(self):
        self.client = APIClient()

    @patch('project.apps.translate.utils.beancount_validator.BeancountValidator.validate_entries')
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_confirm_write_success_multiple_files(
        self, mock_get_bean_path, mock_validate, user, entry_review_task, parse_file,
        directory, tmp_path,
    ):
        """多文件按 file_id 分组写入：两个 .bean 都写入，队列清空，待办完成"""
        self.client.force_authenticate(user=user)

        parse_file2 = _create_second_parse_file(user, directory)

        _save_review(parse_file.file_id, [_make_entry('entry-1')])
        _save_review(parse_file2.file_id, [_make_entry('entry-2')])
        _enqueue(user, [
            {'file_id': parse_file.file_id, 'uuid': 'entry-1'},
            {'file_id': parse_file2.file_id, 'uuid': 'entry-2'},
        ])

        mock_validate.return_value = (True, None, [])

        bean_paths = {}

        def _bean_path(user_arg, filename, relative_dir=''):
            path = tmp_path / f'{filename}.bean'
            bean_paths[filename] = path
            return str(path)

        mock_get_bean_path.side_effect = _bean_path

        response = self.client.post('/api/translate/entry-review/confirm')

        assert response.status_code == status.HTTP_200_OK
        assert '确认写入成功' in response.data['message']
        assert len(response.data['files']) == 2

        # 两个文件都写入并置为 parsed
        parse_file.refresh_from_db()
        parse_file2.refresh_from_db()
        assert parse_file.status == 'parsed'
        assert parse_file2.status == 'parsed'
        assert bean_paths[parse_file.file.name].read_text(encoding='utf-8') != ''
        assert bean_paths[parse_file2.file.name].read_text(encoding='utf-8') != ''

        # 队列清空且待办完成
        assert EntryReviewQueueService.is_empty(user.id) is True
        entry_review_task.refresh_from_db()
        assert entry_review_task.status == 'completed'

    @patch('project.apps.translate.utils.beancount_validator.BeancountValidator.validate_entries')
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_confirm_write_validation_error_writes_nothing(
        self, mock_get_bean_path, mock_validate, user, entry_review_task, parse_file, tmp_path,
    ):
        """任一文件校验失败时不写入任何文件，队列与状态均不变"""
        self.client.force_authenticate(user=user)

        _save_review(parse_file.file_id, [
            _make_entry('entry-bad', formatted='invalid beancount syntax'),
        ])
        _enqueue(user, [{'file_id': parse_file.file_id, 'uuid': 'entry-bad'}])

        mock_validate.return_value = (False, 'Syntax error', ['Error message'])
        bean_file = tmp_path / 'test_file.csv.bean'
        mock_get_bean_path.return_value = str(bean_file)

        response = self.client.post('/api/translate/entry-review/confirm')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Beancount 语法错误' in response.data['error']
        assert 'error_entries' in response.data
        assert response.data['error_entries'][0]['uuid'] == 'entry-bad'

        # 未写盘
        assert not bean_file.exists()
        # 状态与队列不变
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending_review'
        entry_review_task.refresh_from_db()
        assert entry_review_task.status == 'pending'
        assert EntryReviewQueueService.list_refs(user.id) == [
            {'file_id': parse_file.file_id, 'uuid': 'entry-bad'}
        ]

    def test_confirm_write_empty_queue(self, user, entry_review_task):
        """队列为空时返回 400"""
        self.client.force_authenticate(user=user)

        response = self.client.post('/api/translate/entry-review/confirm')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == '待审核队列为空'

    def test_confirm_write_task_completed(self, user, entry_review_task_completed, parse_file):
        """待办已完成时拒绝确认写入"""
        self.client.force_authenticate(user=user)

        _save_review(parse_file.file_id, [_make_entry('entry-1')])
        _enqueue(user, [{'file_id': parse_file.file_id, 'uuid': 'entry-1'}])

        response = self.client.post('/api/translate/entry-review/confirm')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == '待办任务已完成或已取消'


@pytest.mark.django_db
class TestEntryReviewReparseAllView:
    """POST /api/translate/entry-review/reparse-all 测试"""

    def setup_method(self):
        self.client = APIClient()

    @patch('project.apps.translate.tasks.parse_single_file_task')
    def test_reparse_all_success(self, mock_parse_task, user, entry_review_task, parse_file):
        """成功提交重新解析任务"""
        self.client.force_authenticate(user=user)

        # Mock parse_single_file_task.delay 避免实际执行
        mock_async_result = MagicMock()
        mock_async_result.id = 'test-celery-task-id'
        mock_delay = MagicMock(return_value=mock_async_result)
        mock_parse_task.delay = mock_delay

        response = self.client.post(
            '/api/translate/entry-review/reparse-all',
            {'file_id': parse_file.file_id},
            format='json',
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert '重新解析任务已提交' in response.data['message']
        assert response.data['celery_task_id'] == 'test-celery-task-id'

        # 验证 ParseFile 状态重置为 pending
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending'

        # 验证异步任务已创建
        mock_delay.assert_called_once()

    def test_reparse_all_task_completed(self, user, entry_review_task_completed, parse_file):
        """待办已完成时拒绝重新解析"""
        self.client.force_authenticate(user=user)

        response = self.client.post(
            '/api/translate/entry-review/reparse-all',
            {'file_id': parse_file.file_id},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == '待办任务已完成或已取消'

    def test_reparse_all_file_not_found(self, user, entry_review_task):
        """file_id 对应文件不存在"""
        self.client.force_authenticate(user=user)

        response = self.client.post(
            '/api/translate/entry-review/reparse-all',
            {'file_id': 999999},
            format='json',
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == '文件不存在'

    @patch('project.apps.translate.tasks.parse_single_file_task')
    def test_reparse_all_allowed_when_review_expired(
        self, mock_parse_task, user, entry_review_task, parse_file,
    ):
        """审核已过期仍允许重新解析全部条目"""
        self.client.force_authenticate(user=user)

        mock_async_result = MagicMock()
        mock_async_result.id = 'test-celery-task-id'
        mock_parse_task.delay = MagicMock(return_value=mock_async_result)

        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [],
            'created_at': time.time() - 86400,
            'review_expires_at': time.time() - 3600,
        })

        response = self.client.post(
            '/api/translate/entry-review/reparse-all',
            {'file_id': parse_file.file_id},
            format='json',
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['celery_task_id'] == 'test-celery-task-id'

    @patch('project.apps.translate.tasks.parse_single_file_task')
    def test_reparse_all_passes_password_to_task(
        self, mock_parse_task, user, entry_review_task, parse_file,
    ):
        """reparse-all 可将解密密码传入 Celery 任务参数。"""
        self.client.force_authenticate(user=user)

        mock_async_result = MagicMock()
        mock_async_result.id = 'test-celery-task-id'
        mock_delay = MagicMock(return_value=mock_async_result)
        mock_parse_task.delay = mock_delay

        response = self.client.post(
            '/api/translate/entry-review/reparse-all',
            {'file_id': parse_file.file_id, 'password': 'secret123'},
            format='json',
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0][2]
        assert args['password'] == 'secret123'


@pytest.mark.django_db
class TestParseTaskStatusView:
    def setup_method(self):
        self.client = APIClient()

    def test_get_parse_task_status(self, user, parse_file):
        from django.core.cache import cache

        self.client.force_authenticate(user=user)
        cache.set('task_status:celery-123', {
            'status': 'pending_review',
            'file_id': parse_file.file_id,
            'error': None,
        }, timeout=3600)

        response = self.client.get('/api/translate/parse-task-status', {'task_id': 'celery-123'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending_review'
        assert response.data['file_id'] == parse_file.file_id


@pytest.mark.django_db
class TestCancelParseView:
    """CancelParseView 测试"""

    def setup_method(self):
        self.client = APIClient()

    def test_cancel_parse_deactivates_entry_review_task_when_queue_empty(
        self, user, entry_review_task, parse_file
    ):
        """取消解析后队列为空，entry_review 待办置为 inactive"""
        self.client.force_authenticate(user=user)

        # 保证文件状态可取消
        parse_file.status = 'parsed'
        parse_file.save()

        # 保存缓存并入队，使引用有效
        _save_review(parse_file.file_id, [_make_entry('entry-1')])
        _enqueue(user, [{'file_id': parse_file.file_id, 'uuid': 'entry-1'}])

        response = self.client.post('/api/translate/cancel', {
            'file_ids': [parse_file.file_id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK

        parse_file.refresh_from_db()
        assert parse_file.status == 'cancelled'

        # 该文件引用已从队列移除
        assert EntryReviewQueueService.list_refs(user.id) == []

        # 队列为空 -> 待办未激活
        entry_review_task.refresh_from_db()
        assert entry_review_task.status == 'inactive'

    def test_cancel_parse_multiple_files(self, user, parse_file, directory):
        """批量取消解析"""
        self.client.force_authenticate(user=user)

        parse_file2 = _create_second_parse_file(user, directory)

        parse_file.status = 'pending'
        parse_file.save()
        parse_file2.status = 'pending'
        parse_file2.save()

        response = self.client.post('/api/translate/cancel', {
            'file_ids': [parse_file.file_id, parse_file2.file_id]
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cancelled_files']) == 2

        parse_file.refresh_from_db()
        parse_file2.refresh_from_db()
        assert parse_file.status == 'cancelled'
        assert parse_file2.status == 'cancelled'
