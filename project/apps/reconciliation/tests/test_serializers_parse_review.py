"""
ScheduledTaskListSerializer 解析审核相关测试
"""
import pytest
import time
from django.contrib.contenttypes.models import ContentType

from project.apps.reconciliation.models import ScheduledTask
from project.apps.reconciliation.serializers import ScheduledTaskListSerializer
from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.file_manager.models import File, Directory
from project.apps.translate.models import ParseFile


@pytest.fixture
def parse_file_for_serializer(user):
    """创建 ParseFile 用于序列化器测试"""
    directory = Directory.objects.create(name='test_dir', owner=user)
    file_obj = File.objects.create(
        name='test_file.csv',
        directory=directory,
        storage_name='test_storage_name',
        size=1024,
        owner=user,
        content_type='text/csv'
    )
    return ParseFile.objects.create(file=file_obj, status='pending_review')


@pytest.fixture
def parse_review_task_for_serializer(user, parse_file_for_serializer):
    """创建解析审核待办任务用于序列化器测试"""
    content_type = ContentType.objects.get_for_model(ParseFile)
    return ScheduledTask.objects.create(
        task_type='parse_review',
        content_type=content_type,
        object_id=parse_file_for_serializer.file_id,
        status='pending'
    )


@pytest.fixture
def mock_parse_result_data_for_serializer(parse_file_for_serializer):
    """模拟解析结果数据用于序列化器测试"""
    current_time = time.time()
    return {
        'file_id': parse_file_for_serializer.file_id,
        'formatted_data': [
            {
                'uuid': 'entry-1',
                'formatted': '2025-01-20 * "Test" "Transaction 1"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                'edited_formatted': '2025-01-20 * "Test" "Transaction 1"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                'selected_expense_key': 'Expenses:Test',
                'expense_candidates_with_score': [
                    {'key': 'Expenses:Test', 'score': 0.9}
                ],
                'original_row': {'date': '2025-01-20', 'description': 'Test Transaction 1', 'amount': 100.00}
            }
        ],
        'created_at': current_time,
        'review_expires_at': current_time + 86400  # 24小时后
    }


@pytest.mark.django_db
class TestScheduledTaskListSerializerParseReview:
    """ScheduledTaskListSerializer 解析审核相关测试"""
    
    def test_review_expires_at_for_parse_review(self, user, parse_review_task_for_serializer, parse_file_for_serializer, mock_parse_result_data_for_serializer):
        """测试解析待办任务返回 review_expires_at 字段"""
        ParseReviewService.save_parse_result(parse_file_for_serializer.file_id, mock_parse_result_data_for_serializer)
        
        serializer = ScheduledTaskListSerializer(parse_review_task_for_serializer)
        data = serializer.data
        
        assert 'review_expires_at' in data
        assert data['review_expires_at'] == mock_parse_result_data_for_serializer['review_expires_at']
    
    def test_review_expires_at_for_parse_review_cache_not_exists(self, user, parse_review_task_for_serializer, parse_file_for_serializer):
        """测试缓存不存在时回退到 task.created + 24h"""
        ParseReviewService.delete_parse_result(parse_file_for_serializer.file_id)
        
        serializer = ScheduledTaskListSerializer(parse_review_task_for_serializer)
        data = serializer.data
        
        assert 'review_expires_at' in data
        expected = parse_review_task_for_serializer.created.timestamp() + ParseReviewService.REVIEW_DEADLINE_SECONDS
        assert data['review_expires_at'] == pytest.approx(expected, abs=1)
    
    def test_review_expires_at_for_reconciliation(self, user, scheduled_task_pending):
        """测试对账待办任务不返回 review_expires_at"""
        serializer = ScheduledTaskListSerializer(scheduled_task_pending)
        data = serializer.data
        
        assert 'review_expires_at' in data
        assert data['review_expires_at'] is None
    
    def test_file_name_and_file_id_for_parse_review(self, user, parse_review_task_for_serializer, parse_file_for_serializer):
        """测试解析待办任务返回 file_name 和 file_id"""
        serializer = ScheduledTaskListSerializer(parse_review_task_for_serializer)
        data = serializer.data
        
        assert 'file_name' in data
        assert 'file_id' in data
        assert data['file_name'] == parse_file_for_serializer.file.name
        assert data['file_id'] == parse_file_for_serializer.file_id
        
        assert 'account_name' in data
        assert 'account_type' in data
        assert data['account_name'] is None
        assert data['account_type'] is None
    
    def test_account_name_and_account_type_for_reconciliation(self, user, scheduled_task_pending, account):
        """测试对账待办任务返回 account_name 和 account_type"""
        serializer = ScheduledTaskListSerializer(scheduled_task_pending)
        data = serializer.data
        
        assert 'account_name' in data
        assert 'account_type' in data
        assert data['account_name'] == account.account
        assert data['account_type'] == account.get_account_type()
        
        assert 'file_name' in data
        assert 'file_id' in data
        assert data['file_name'] is None
        assert data['file_id'] is None
    
    def test_review_expires_at_updates_after_reparse(self, user, parse_review_task_for_serializer, parse_file_for_serializer, mock_parse_result_data_for_serializer):
        """测试重新解析后 review_expires_at 更新"""
        ParseReviewService.save_parse_result(parse_file_for_serializer.file_id, mock_parse_result_data_for_serializer)
        
        serializer = ScheduledTaskListSerializer(parse_review_task_for_serializer)
        initial_review_expires_at = serializer.data['review_expires_at']
        
        new_review_expires_at = time.time() + 86400
        updated_data = mock_parse_result_data_for_serializer.copy()
        updated_data['review_expires_at'] = new_review_expires_at
        ParseReviewService.save_parse_result(parse_file_for_serializer.file_id, updated_data)
        
        serializer = ScheduledTaskListSerializer(parse_review_task_for_serializer)
        updated_review_expires_at = serializer.data['review_expires_at']
        
        assert updated_review_expires_at == new_review_expires_at
        assert updated_review_expires_at != initial_review_expires_at
