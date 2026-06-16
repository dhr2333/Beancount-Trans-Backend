"""解析审核标签 API 与 service 测试。"""
import pytest
from unittest.mock import patch
from django.core.cache import cache
from rest_framework.test import APIClient

from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.translate.services.tag_merger import merge_tags_with_details
from project.apps.translate.services.parse.transaction_parser import single_parse_transaction
from project.apps.tags.models import Tag


@pytest.mark.django_db
class TestMergeTagsWithDetails:
    def test_merge_source_and_mapping_sources(self, user):
        tag = Tag.objects.create(name="TagOnly", owner=user)
        merged, details = merge_tags_with_details(
            source_tag="#BillTag",
            mapping_tag_sources=[
                {
                    'tag': tag,
                    'source': {
                        'type': 'mapping',
                        'key': '十月结晶',
                        'mapping_type': 'expense',
                    },
                }
            ],
        )
        assert merged == "#BillTag #TagOnly"
        assert len(details) == 2
        bill = next(item for item in details if item['path'] == 'BillTag')
        assert bill['sources'] == [{'type': 'source'}]
        mapped = next(item for item in details if item['path'] == 'TagOnly')
        assert mapped['sources'][0]['key'] == '十月结晶'


@pytest.mark.django_db
class TestParseReviewTagOverrides:
    def setup_method(self):
        cache.clear()

    def test_apply_tag_overrides_remove_and_add(self):
        tag_details = [
            {'path': 'Keep', 'sources': [{'type': 'mapping', 'key': 'A', 'mapping_type': 'expense'}]},
            {'path': 'Drop', 'sources': [{'type': 'mapping', 'key': 'B', 'mapping_type': 'expense'}]},
        ]
        overrides = {
            'removed_paths': ['Drop'],
            'added_paths': ['Manual/Tag'],
        }
        effective = ParseReviewService.apply_tag_overrides(tag_details, overrides)
        paths = [item['path'] for item in effective]
        assert paths == ['Keep', 'Manual/Tag']
        manual = effective[1]
        assert manual['sources'] == [{'type': 'manual'}]

    def test_set_header_tags_replace(self):
        formatted = (
            '2025-01-20 * "Payee" "Note" #OldTag\n'
            '    Expenses:Test  100.00 CNY\n'
        )
        updated = ParseReviewService.set_header_tags(formatted, ['New/Tag', 'Keep'])
        assert '#OldTag' not in updated.split('\n')[0]
        assert '#New/Tag #Keep' in updated.split('\n')[0]

    def test_set_header_tags_preserves_hash_inside_quoted_note(self):
        formatted = (
            '2025-07-26 * "payee" "顾客打赏-#8袁记云饺(龙湾海城店)"\n'
            '    Expenses:Test  2.00 CNY\n'
        )
        updated = ParseReviewService.set_header_tags(formatted, [])
        assert updated.split('\n')[0] == (
            '2025-07-26 * "payee" "顾客打赏-#8袁记云饺(龙湾海城店)"'
        )
        assert not ParseReviewService._entry_header_has_tags({'formatted': formatted})

    def test_parse_source_tag_paths_skips_invalid_merchant_hash(self):
        from project.apps.translate.services.tag_merger import parse_source_tag_paths

        assert parse_source_tag_paths('#8袁记云饺(龙湾海城店)') == []
        assert parse_source_tag_paths('#BillTag') == ['BillTag']

    def test_update_entry_tags_remove_persists_on_reparse_base(self):
        file_id = 42
        ParseReviewService.save_parse_result(file_id, {
            'file_id': file_id,
            'formatted_data': [{
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Payee" "Note" #Drop #Keep\n    Expenses:Test  1 CNY\n',
                'edited_formatted': '2025-01-20 * "Payee" "Note" #Drop #Keep\n    Expenses:Test  1 CNY\n',
                'tag_details': [
                    {'path': 'Drop', 'sources': [{'type': 'mapping', 'key': 'A', 'mapping_type': 'expense'}]},
                    {'path': 'Keep', 'sources': [{'type': 'mapping', 'key': 'B', 'mapping_type': 'expense'}]},
                ],
                'tag_overrides': ParseReviewService.default_tag_overrides(),
            }],
        })

        result = ParseReviewService.update_entry_tags(file_id, 'entry-1', 'remove', 'Drop')
        assert result is not None
        assert '#Drop' not in result['edited_formatted']
        assert '#Keep' in result['edited_formatted']
        assert 'Drop' in result['tag_overrides']['removed_paths']

        ParseReviewService.update_entry_formatted(
            file_id,
            'entry-1',
            '2025-01-20 * "Payee" "Note" #Drop #Keep\n    Expenses:Test  1 CNY\n',
            tag_details=[
                {'path': 'Drop', 'sources': [{'type': 'mapping', 'key': 'A', 'mapping_type': 'expense'}]},
                {'path': 'Keep', 'sources': [{'type': 'mapping', 'key': 'B', 'mapping_type': 'expense'}]},
            ],
        )
        cached = ParseReviewService.get_parse_result(file_id)
        entry = cached['formatted_data'][0]
        assert '#Drop' not in entry['edited_formatted']
        assert 'Drop' in entry['tag_overrides']['removed_paths']


@pytest.mark.django_db
class TestParseReviewTagDetailsBackfill:
    def setup_method(self):
        cache.clear()

    @patch('project.apps.translate.services.handlers.get_default_assets')
    def test_ensure_entry_tag_details_backfills_missing_sources(
        self,
        mock_assets,
        user,
    ):
        from project.apps.account.models import Account
        from project.apps.maps.models import Expense
        from project.apps.translate.tests.test_mapping_tags_without_account import (
            _default_assets,
            _expense_row,
            _parse_config,
        )

        mock_assets.return_value = _default_assets()
        tag = Tag.objects.create(name="Irregular", owner=user)
        mapping = Expense.objects.create(
            key="十月结晶",
            expend=None,
            owner=user,
            enable=True,
        )
        mapping.tags.add(tag)

        parsed = single_parse_transaction(
            _expense_row(),
            user.id,
            _parse_config(),
            None,
        )
        formatted = (
            f'2024-02-25 * "十月结晶" "十月结晶会员出行必备" {parsed["tag"]}\n'
            f'    Expenses:Other 14.80 CNY\n'
            f'    Assets:Digital:Alipay -14.80 CNY\n'
        )
        entry = {
            'uuid': 'entry-backfill',
            'formatted': formatted,
            'edited_formatted': formatted,
            'selected_expense_key': parsed['selected_expense_key'],
            'expense_candidates_with_score': parsed['expense_candidates_with_score'],
            'original_row': _expense_row(),
            'tag_details': [],
            'tag_overrides': ParseReviewService.default_tag_overrides(),
        }

        changed = ParseReviewService.ensure_entry_tag_details(
            entry,
            user.id,
            _parse_config(),
            user=user,
        )
        assert changed is True
        assert any(item['path'] == 'Irregular' for item in entry['tag_details'])
        irregular = next(item for item in entry['tag_details'] if item['path'] == 'Irregular')
        assert irregular['sources'][0]['key'] == '十月结晶'


@pytest.mark.django_db
class TestParseReviewTagsView:
    def setup_method(self):
        cache.clear()
        self.client = APIClient()

    def test_patch_remove_tag(self, user, parse_review_task, parse_file):
        self.client.force_authenticate(user=user)
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [{
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Payee" "Note" #RemoveMe\n    Expenses:Test  1 CNY\n',
                'edited_formatted': '2025-01-20 * "Payee" "Note" #RemoveMe\n    Expenses:Test  1 CNY\n',
                'tag_details': [
                    {'path': 'RemoveMe', 'sources': [{'type': 'manual'}]},
                ],
                'tag_overrides': ParseReviewService.default_tag_overrides(),
            }],
        })

        response = self.client.patch(
            f'/api/translate/parse-review/{parse_review_task.id}/entries/entry-1/tags',
            {'action': 'remove', 'tag_path': 'RemoveMe'},
            format='json',
        )
        assert response.status_code == 200
        assert '#RemoveMe' not in response.data['edited_formatted']
        assert 'RemoveMe' in response.data['tag_overrides']['removed_paths']

    def test_patch_add_tag(self, user, parse_review_task, parse_file):
        self.client.force_authenticate(user=user)
        ParseReviewService.save_parse_result(parse_file.file_id, {
            'file_id': parse_file.file_id,
            'formatted_data': [{
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Payee" "Note"\n    Expenses:Test  1 CNY\n',
                'edited_formatted': '2025-01-20 * "Payee" "Note"\n    Expenses:Test  1 CNY\n',
                'tag_details': [],
                'tag_overrides': ParseReviewService.default_tag_overrides(),
            }],
        })

        response = self.client.patch(
            f'/api/translate/parse-review/{parse_review_task.id}/entries/entry-1/tags',
            {'action': 'add', 'tag_path': 'Manual/Added'},
            format='json',
        )
        assert response.status_code == 200
        assert '#Manual/Added' in response.data['edited_formatted']
        assert 'Manual/Added' in response.data['tag_overrides']['added_paths']
