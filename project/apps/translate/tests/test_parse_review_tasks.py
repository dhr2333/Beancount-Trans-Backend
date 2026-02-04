"""
解析审核任务处理逻辑测试
"""
import pytest
import time
from unittest.mock import patch, MagicMock, Mock
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.contenttypes.models import ContentType

from project.apps.translate.models import ParseFile, FormatConfig
from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.reconciliation.models import ScheduledTask
from project.apps.translate.tasks import parse_single_file_task, auto_confirm_expired_parse_reviews


@pytest.mark.django_db
class TestParseSingleFileTask:
    """parse_single_file_task 任务测试"""
    
    def setup_method(self):
        """设置测试环境"""
        pass
    
    @patch('project.apps.translate.tasks.get_storage_client')
    @patch('project.apps.translate.tasks.AnalyzeService')
    @patch('project.utils.tools.get_user_config')
    def test_parse_task_review_mode(self, mock_get_config, mock_analyze_service, mock_storage_client, user, parse_file):
        """测试审核模式下不写入文件，缓存数据保存，状态更新"""
        # Mock 存储客户端
        mock_storage = MagicMock()
        mock_file_data = Mock()
        mock_file_data.read.return_value = b'test,file,content'
        mock_storage.download_file.return_value = mock_file_data
        mock_storage_client.return_value = mock_storage
        
        # Mock 配置 - 使用 get_or_create 避免唯一约束冲突
        from project.apps.translate.models import FormatConfig
        config, _ = FormatConfig.objects.get_or_create(
            owner=user,
            defaults={'parsing_mode_preference': 'review'}
        )
        mock_get_config.return_value = config
        
        # Mock AnalyzeService
        mock_service = MagicMock()
        mock_service.analyze_single_file.return_value = {
            'formatted_data': [
                {
                    'id': 'cache-key-1',
                    'formatted': '2025-01-20 * "Test" "Transaction"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                    'selected_expense_key': 'Expenses:Test',
                    'expense_candidates_with_score': []
                }
            ],
            'parsed_data': [
                {
                    'cache_key': 'cache-key-1',
                    'uuid': 'uuid-1'
                }
            ]
        }
        mock_analyze_service.return_value = mock_service
        
        # Mock cache.get 返回 original_row
        from django.core.cache import cache
        cache.set('cache-key-1', {'original_row': {'date': '2025-01-20', 'description': 'Test'}}, timeout=3600)
        
        # 创建 inactive 状态的 ScheduledTask
        content_type = ContentType.objects.get_for_model(ParseFile)
        parse_review_task = ScheduledTask.objects.create(
            task_type='parse_review',
            content_type=content_type,
            object_id=parse_file.file_id,
            status='inactive'
        )
        
        # 执行任务（审核模式）
        args = {
            'write': False,  # 审核模式
            'cmb_credit_ignore': True,
            'boc_debit_ignore': True,
            'password': None,
            'balance': False,
            'isCSVOnly': False
        }
        
        # 创建模拟的 Celery 任务请求
        mock_request = MagicMock()
        mock_request.id = 'test-task-id'
        
        # 手动调用任务函数（不使用 .delay）
        # 对于绑定任务，由于 CELERY_TASK_ALWAYS_EAGER=True，使用 apply() 会同步执行
        # apply() 会自动创建任务实例并设置 self.request
        result = parse_single_file_task.apply(
            args=[parse_file.file_id, user.id, args],
            task_id='test-task-id'
        )
        # 在 CELERY_TASK_ALWAYS_EAGER=True 模式下，apply() 返回的结果可以直接使用
        if hasattr(result, 'result'):
            result = result.result
        
        # 验证返回结果
        assert result['status'] == 'pending_review'
        assert result['file_id'] == parse_file.file_id
        
        # 验证 ParseFile 状态更新为 pending_review
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending_review'
        
        # 验证 ScheduledTask 状态更新为 pending
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'pending'
        
        # 验证缓存数据保存
        cached_data = ParseReviewService.get_parse_result(parse_file.file_id)
        assert cached_data is not None
        assert cached_data['file_id'] == parse_file.file_id
        assert len(cached_data['formatted_data']) == 1
        assert 'expires_at' in cached_data
        assert cached_data['expires_at'] > time.time()
        
        # 验证缓存数据包含必要的字段
        entry = cached_data['formatted_data'][0]
        assert 'uuid' in entry
        assert 'formatted' in entry
        assert 'edited_formatted' in entry
        assert 'original_row' in entry
    
    @patch('project.apps.translate.tasks.get_storage_client')
    @patch('project.apps.translate.tasks.AnalyzeService')
    @patch('project.utils.tools.get_user_config')
    def test_parse_task_direct_write_mode(self, mock_get_config, mock_analyze_service, mock_storage_client, user, parse_file):
        """测试直接写入模式下立即写入文件，状态更新"""
        # Mock 存储客户端
        mock_storage = MagicMock()
        mock_file_data = Mock()
        mock_file_data.read.return_value = b'test,file,content'
        mock_storage.download_file.return_value = mock_file_data
        mock_storage_client.return_value = mock_storage
        
        # Mock 配置 - 使用 get_or_create 避免唯一约束冲突
        from project.apps.translate.models import FormatConfig
        config, _ = FormatConfig.objects.get_or_create(
            owner=user,
            defaults={'parsing_mode_preference': 'direct_write'}
        )
        mock_get_config.return_value = config
        
        # Mock AnalyzeService
        mock_service = MagicMock()
        mock_service.analyze_single_file.return_value = {
            'formatted_data': [],
            'parsed_data': []
        }
        mock_analyze_service.return_value = mock_service
        
        # 创建 inactive 状态的 ScheduledTask
        content_type = ContentType.objects.get_for_model(ParseFile)
        parse_review_task = ScheduledTask.objects.create(
            task_type='parse_review',
            content_type=content_type,
            object_id=parse_file.file_id,
            status='inactive'
        )
        
        # 执行任务（直接写入模式）
        args = {
            'write': True,  # 直接写入模式
            'cmb_credit_ignore': True,
            'boc_debit_ignore': True,
            'password': None,
            'balance': False,
            'isCSVOnly': False
        }
        
        # 手动调用任务函数
        # 对于绑定任务，由于 CELERY_TASK_ALWAYS_EAGER=True，使用 apply() 会同步执行
        result = parse_single_file_task.apply(
            args=[parse_file.file_id, user.id, args],
            task_id='test-task-id'
        )
        # 在 CELERY_TASK_ALWAYS_EAGER=True 模式下，apply() 返回的结果可以直接使用
        if hasattr(result, 'result'):
            result = result.result
        
        # 验证返回结果
        assert result['status'] == 'parsed'
        assert result['file_id'] == parse_file.file_id
        
        # 验证 ParseFile 状态更新为 parsed
        parse_file.refresh_from_db()
        assert parse_file.status == 'parsed'
        
        # 验证 ScheduledTask 保持 inactive 状态
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'inactive'
    


@pytest.mark.django_db
class TestAutoConfirmExpiredParseReviews:
    """auto_confirm_expired_parse_reviews 定时任务测试"""
    
    def setup_method(self):
        """设置测试环境"""
        pass
    
    @patch('project.apps.translate.utils.beancount_validator.BeancountValidator.validate_entries')
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_auto_confirm_expired_tasks(self, mock_get_bean_path, mock_validate, user, parse_review_task, parse_file, tmp_path):
        """测试自动确认过期任务（基于 created 时间，超过24小时）"""
        from datetime import timedelta
        from django.utils import timezone
        
        # 设置任务的创建时间为25小时前（已过期）
        expired_time = timezone.now() - timedelta(hours=25)
        parse_review_task.created = expired_time
        parse_review_task.save()
        
        # 创建缓存数据
        expired_data = {
            'file_id': parse_file.file_id,
            'formatted_data': [
                {
                    'uuid': 'entry-1',
                    'formatted': '2025-01-20 * "Test" "Transaction"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                    'edited_formatted': '2025-01-20 * "Test" "Transaction"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                    'original_row': {}
                }
            ],
            'created_at': time.time() - 86400,
            'expires_at': time.time() + 86400
        }
        ParseReviewService.save_parse_result(parse_file.file_id, expired_data)
        
        # Mock Beancount 校验
        mock_validate.return_value = (True, None, [])
        
        # Mock bean 文件路径
        bean_file = tmp_path / 'test_file.bean'
        bean_file.write_text('', encoding='utf-8')
        mock_get_bean_path.return_value = str(bean_file)
        
        # 执行定时任务
        auto_confirm_expired_parse_reviews()
        
        # 验证 ParseFile 状态更新为 parsed
        parse_file.refresh_from_db()
        assert parse_file.status == 'parsed'
        
        # 验证 ScheduledTask 状态更新为 completed
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'completed'
        
        # 验证文件已写入
        assert bean_file.read_text(encoding='utf-8') != ''
    
    @patch('project.apps.translate.utils.beancount_validator.BeancountValidator.validate_entries')
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_auto_confirm_expired_tasks_validation_error(self, mock_get_bean_path, mock_validate, user, parse_review_task, parse_file, tmp_path):
        """测试自动确认过期任务时 Beancount 语法错误"""
        from datetime import timedelta
        from django.utils import timezone
        
        # 设置任务的创建时间为25小时前（已过期）
        expired_time = timezone.now() - timedelta(hours=25)
        parse_review_task.created = expired_time
        parse_review_task.save()
        
        # 创建缓存数据（包含语法错误）
        expired_data = {
            'file_id': parse_file.file_id,
            'formatted_data': [
                {
                    'uuid': 'entry-1',
                    'formatted': 'invalid beancount syntax',
                    'edited_formatted': 'invalid beancount syntax',
                    'original_row': {}
                }
            ],
            'created_at': time.time() - 86400,
            'expires_at': time.time() + 86400
        }
        ParseReviewService.save_parse_result(parse_file.file_id, expired_data)
        
        # Mock Beancount 校验返回错误
        mock_validate.return_value = (False, 'Syntax error', ['Error message'])
        
        # Mock bean 文件路径（避免实际写入文件）
        bean_file = tmp_path / 'test_file.bean'
        mock_get_bean_path.return_value = str(bean_file)
        
        # 执行定时任务
        auto_confirm_expired_parse_reviews()
        
        # 验证 ParseFile 状态未更新（因为校验失败）
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending_review'  # 保持原状态
        
        # 验证 ScheduledTask 状态未更新
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'pending'  # 保持原状态
    
    def test_auto_confirm_expired_tasks_not_expired(self, user, parse_review_task, parse_file):
        """测试未过期的任务不会被处理（基于 created 时间）"""
        from datetime import timedelta
        from django.utils import timezone
        
        # 设置任务的创建时间为23小时前（未过期）
        recent_time = timezone.now() - timedelta(hours=23)
        parse_review_task.created = recent_time
        parse_review_task.save()
        
        # 创建缓存数据
        future_data = {
            'file_id': parse_file.file_id,
            'formatted_data': [
                {
                    'uuid': 'entry-1',
                    'formatted': '2025-01-20 * "Test" "Transaction"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                    'edited_formatted': '2025-01-20 * "Test" "Transaction"\n    Expenses:Test  100.00 CNY\n    Assets:Test  -100.00 CNY\n',
                    'original_row': {}
                }
            ],
            'created_at': time.time(),
            'expires_at': time.time() + 86400
        }
        ParseReviewService.save_parse_result(parse_file.file_id, future_data)
        
        # 执行定时任务
        auto_confirm_expired_parse_reviews()
        
        # 验证任务未处理（因为未过期）
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending_review'  # 保持原状态
        
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'pending'  # 保持原状态

