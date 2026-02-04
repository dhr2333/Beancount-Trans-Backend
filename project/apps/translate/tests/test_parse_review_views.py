"""
ParseReviewViewSet API 测试
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status

from project.apps.translate.services.parse_review_service import ParseReviewService
from project.apps.translate.models import ParseFile
from project.apps.reconciliation.models import ScheduledTask


@pytest.mark.django_db
class TestParseReviewResultsView:
    """ParseReviewResultsView API 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    def test_get_parse_results_success(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试成功获取解析结果"""
        self.client.force_authenticate(user=user)
        
        # 保存解析结果到缓存
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.get(f'/api/translate/parse-review/{parse_review_task.id}/results')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'formatted_data' in response.data
        assert len(response.data['formatted_data']) == 2
        
        # 验证去除末尾换行符
        for entry in response.data['formatted_data']:
            assert not entry['formatted'].endswith('\n')
            assert not entry['edited_formatted'].endswith('\n')
    
    def test_get_parse_results_not_found_task(self, user):
        """测试处理任务不存在的情况"""
        self.client.force_authenticate(user=user)
        
        response = self.client.get('/api/translate/parse-review/99999/results')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_get_parse_results_cache_not_exists(self, user, parse_review_task, parse_file):
        """测试处理缓存不存在的情况"""
        self.client.force_authenticate(user=user)
        
        # 确保缓存不存在
        from project.apps.translate.services.parse_review_service import ParseReviewService
        ParseReviewService.delete_parse_result(parse_file.file_id)
        
        response = self.client.get(f'/api/translate/parse-review/{parse_review_task.id}/results')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '解析结果不存在或已过期' in response.data['error']
    
    def test_get_parse_results_task_completed(self, user, parse_review_task_completed, parse_file, mock_parse_result_data):
        """测试处理任务已完成的情况"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.get(f'/api/translate/parse-review/{parse_review_task_completed.id}/results')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已完成或已取消' in response.data['error']
    
    def test_get_parse_results_permission_denied(self, user, other_user, parse_review_task, parse_file, mock_parse_result_data):
        """测试验证只能访问自己的文件"""
        self.client.force_authenticate(user=other_user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.get(f'/api/translate/parse-review/{parse_review_task.id}/results')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_parse_results_unauthenticated(self, parse_review_task):
        """测试验证未认证用户无法访问"""
        response = self.client.get(f'/api/translate/parse-review/{parse_review_task.id}/results')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestParseReviewReparseView:
    """ParseReviewReparseView API 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    @patch('project.apps.translate.views.views.single_parse_transaction')
    @patch('project.apps.translate.views.views.FormatData.format_instance')
    @patch('project.apps.translate.views.views.get_user_config')
    def test_reparse_entry_success(self, mock_get_config, mock_format, mock_parse, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试成功重解析单个条目"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        # Mock 解析和格式化
        mock_get_config.return_value = MagicMock()
        mock_parse.return_value = {
            'expense_candidates_with_score': [{'key': 'Expenses:Updated', 'score': 0.95}]
        }
        mock_format.return_value = '2025-01-20 * "Updated" "Transaction"\n    Expenses:Updated  150.00 CNY\n    Assets:Test  -150.00 CNY\n'
        
        response = self.client.post(
            f'/api/translate/parse-review/{parse_review_task.id}/reparse',
            {
                'entry_uuid': 'entry-1',
                'selected_key': 'Expenses:Updated'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == 'entry-1'
        assert 'formatted' in response.data
        assert 'edited_formatted' in response.data
        assert response.data['selected_expense_key'] == 'Expenses:Updated'
        
        # 验证缓存已更新
        cached_data = ParseReviewService.get_parse_result(parse_file.file_id)
        updated_entry = next((e for e in cached_data['formatted_data'] if e['uuid'] == 'entry-1'), None)
        assert updated_entry is not None
    
    def test_reparse_entry_missing_entry_uuid(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试处理缺少 entry_uuid 参数"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.post(
            f'/api/translate/parse-review/{parse_review_task.id}/reparse',
            {
                'selected_key': 'Expenses:Test'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']
    
    def test_reparse_entry_missing_selected_key(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试处理缺少 selected_key 参数"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.post(
            f'/api/translate/parse-review/{parse_review_task.id}/reparse',
            {
                'entry_uuid': 'entry-1'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']
    
    def test_reparse_entry_uuid_not_found(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试处理条目 UUID 不存在的情况"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.post(
            f'/api/translate/parse-review/{parse_review_task.id}/reparse',
            {
                'entry_uuid': 'non-existent-uuid',
                'selected_key': 'Expenses:Test'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '未找到对应的条目' in response.data['error']
    
    # @patch('project.apps.translate.views.views.single_parse_transaction')
    # @patch('project.apps.translate.views.views.FormatData.format_instance')
    # @patch('project.apps.translate.views.views.get_user_config')
    # def test_reparse_entry_cache_not_exists(self, mock_get_config, mock_format, mock_parse, user, parse_review_task):
    #     """测试处理缓存不存在的情况"""
    #     self.client.force_authenticate(user=user)
        
    #     response = self.client.post(
    #         f'/api/translate/parse-review/{parse_review_task.id}/reparse',
    #         {
    #             'entry_uuid': 'entry-1',
    #             'selected_key': 'Expenses:Test'
    #         },
    #         format='json'
    #     )
        
    #     assert response.status_code == status.HTTP_404_NOT_FOUND
    #     assert '解析结果不存在或已过期' in response.data['error']


@pytest.mark.django_db
class TestParseReviewEditView:
    """ParseReviewEditView API 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    def test_update_entry_edit_success(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试成功更新编辑内容"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        new_edited_formatted = '2025-01-20 * "Edited" "Transaction"\n    Expenses:Edited  150.00 CNY\n    Assets:Test  -150.00 CNY\n'
        
        response = self.client.put(
            f'/api/translate/parse-review/{parse_review_task.id}/entries/entry-1/edit',
            {
                'edited_formatted': new_edited_formatted
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
    
    def test_update_entry_edit_missing_params(self, user, parse_review_task, parse_file, mock_parse_result_data):
        """测试处理缺少 edited_formatted 参数"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.put(
            f'/api/translate/parse-review/{parse_review_task.id}/entries/entry-1/edit',
            {},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '缺少必要参数' in response.data['error']


@pytest.mark.django_db
class TestParseReviewConfirmView:
    """ParseReviewConfirmView API 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_confirm_write_success(self, mock_get_bean_path, user, parse_review_task, parse_file, mock_parse_result_data, tmp_path):
        """测试成功确认写入"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        # Mock bean 文件路径
        bean_file = tmp_path / 'test_file.bean'
        bean_file.write_text('', encoding='utf-8')
        mock_get_bean_path.return_value = str(bean_file)
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task.id}/confirm')
        
        assert response.status_code == status.HTTP_200_OK
        assert '确认写入成功' in response.data['message']
        
        # 验证 ParseFile 状态更新为 parsed
        parse_file.refresh_from_db()
        assert parse_file.status == 'parsed'
        
        # 验证 ScheduledTask 状态更新为 completed
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'completed'
        
        # 验证文件已写入
        assert bean_file.read_text(encoding='utf-8') != ''
    
    @patch('project.utils.file.BeanFileManager.get_bean_file_path')
    def test_confirm_write_validation_error(self, mock_get_bean_path, user, parse_review_task, parse_file, tmp_path):
        """测试处理 Beancount 语法错误"""
        self.client.force_authenticate(user=user)
        
        # 创建包含语法错误的数据
        invalid_data = {
            'file_id': parse_file.file_id,
            'formatted_data': [
                {
                    'uuid': 'entry-1',
                    'formatted': 'invalid beancount syntax',
                    'edited_formatted': 'invalid beancount syntax',
                    'original_row': {}
                }
            ],
            'created_at': time.time(),
            'expires_at': time.time() + 86400
        }
        ParseReviewService.save_parse_result(parse_file.file_id, invalid_data)
        
        bean_file = tmp_path / 'test_file.bean'
        mock_get_bean_path.return_value = str(bean_file)
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task.id}/confirm')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Beancount 语法错误' in response.data['error']
    
    def test_confirm_write_cache_expired(self, user, parse_review_task, parse_file):
        """测试处理缓存不存在或已过期的情况"""
        self.client.force_authenticate(user=user)
        
        # 确保缓存不存在
        from project.apps.translate.services.parse_review_service import ParseReviewService
        ParseReviewService.delete_parse_result(parse_file.file_id)
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task.id}/confirm')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert '解析结果不存在或已过期' in response.data['error']
    
    def test_confirm_write_task_completed(self, user, parse_review_task_completed, parse_file, mock_parse_result_data):
        """测试处理任务已完成的情况"""
        self.client.force_authenticate(user=user)
        
        ParseReviewService.save_parse_result(parse_file.file_id, mock_parse_result_data)
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task_completed.id}/confirm')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已完成或已取消' in response.data['error']


@pytest.mark.django_db
class TestParseReviewReparseAllView:
    """ParseReviewReparseAllView API 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    @patch('project.apps.translate.tasks.parse_single_file_task')
    @patch('project.apps.translate.views.views.get_user_config')
    def test_reparse_all_success(self, mock_get_config, mock_parse_task, user, parse_review_task, parse_file):
        """测试成功提交重新解析任务"""
        self.client.force_authenticate(user=user)
        
        # 使用 get_or_create 避免唯一约束冲突
        from project.apps.translate.models import FormatConfig
        config, _ = FormatConfig.objects.get_or_create(
            owner=user,
            defaults={'parsing_mode_preference': 'review'}
        )
        mock_get_config.return_value = config
        
        # Mock parse_single_file_task.delay 避免实际执行
        # 在 CELERY_TASK_ALWAYS_EAGER=True 模式下，delay() 会立即执行，所以需要完全 mock
        mock_delay = MagicMock()
        mock_parse_task.delay = mock_delay
        
        # 确保 ParseFile 初始状态不是 pending
        parse_file.status = 'pending_review'
        parse_file.save()
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task.id}/reparse-all')
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert '重新解析任务已提交' in response.data['message']
        
        # 验证 ParseFile 状态重置为 pending（在 try 块中设置）
        parse_file.refresh_from_db()
        assert parse_file.status == 'pending', f"Expected 'pending', but got '{parse_file.status}'. Response: {response.data}"
        
        # 验证异步任务已创建
        mock_delay.assert_called_once()
    
    def test_reparse_all_task_completed(self, user, parse_review_task_completed):
        """测试处理任务已完成的情况"""
        self.client.force_authenticate(user=user)
        
        response = self.client.post(f'/api/translate/parse-review/{parse_review_task_completed.id}/reparse-all')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '已完成或已取消' in response.data['error']


@pytest.mark.django_db
class TestCancelParseView:
    """CancelParseView 测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.client = APIClient()
    
    def test_cancel_parse_updates_task_status_completed(self, user, parse_review_task_completed, parse_file):
        """测试取消解析后，completed 状态的 ScheduledTask 更新为 inactive"""
        self.client.force_authenticate(user=user)
        
        # 确保 ParseFile 状态是可以取消的
        parse_file.status = 'parsed'  # 可以是 pending, processing, parsed
        parse_file.save()
        
        # 保存一些缓存数据
        mock_data = {
            'file_id': parse_file.file_id,
            'formatted_data': [],
            'created_at': time.time(),
            'expires_at': time.time() + 86400
        }
        ParseReviewService.save_parse_result(parse_file.file_id, mock_data)
        
        response = self.client.post('/api/translate/cancel', {
            'file_ids': [parse_file.file_id]
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证 ParseFile 状态更新为 cancelled
        parse_file.refresh_from_db()
        assert parse_file.status == 'cancelled'
        
        # 验证 ScheduledTask 状态更新为 inactive
        parse_review_task_completed.refresh_from_db()
        assert parse_review_task_completed.status == 'inactive'
    
    def test_cancel_parse_updates_task_status_pending(self, user, parse_review_task, parse_file):
        """测试取消解析后，pending 状态的 ScheduledTask 更新为 inactive"""
        self.client.force_authenticate(user=user)
        
        # 确保 ParseFile 状态是可以取消的
        parse_file.status = 'pending'  # 可以是 pending, processing, parsed
        parse_file.save()
        
        response = self.client.post('/api/translate/cancel', {
            'file_ids': [parse_file.file_id]
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # 验证 ParseFile 状态更新为 cancelled
        parse_file.refresh_from_db()
        assert parse_file.status == 'cancelled'
        
        # 验证 ScheduledTask 状态更新为 inactive
        parse_review_task.refresh_from_db()
        assert parse_review_task.status == 'inactive'
    
    def test_cancel_parse_multiple_files(self, user, parse_file):
        """测试批量取消解析"""
        self.client.force_authenticate(user=user)
        
        # 创建另一个文件
        from project.apps.file_manager.models import File, Directory
        directory = Directory.objects.get(id=parse_file.file.directory.id)
        file2 = File.objects.create(
            name='test_file2.csv',
            directory=directory,
            storage_name='test_storage_name2',
            size=1024,
            owner=user,
            content_type='text/csv'
        )
        parse_file2 = ParseFile.objects.create(file=file2, status='pending_review')
        
        # 确保两个文件的状态都是可以取消的
        parse_file.status = 'pending'
        parse_file.save()
        parse_file2.status = 'pending'
        parse_file2.save()
        
        response = self.client.post('/api/translate/cancel', {
            'file_ids': [parse_file.file_id, parse_file2.file_id]
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['cancelled_files']) == 2
        
        # 验证两个文件状态都已更新
        parse_file.refresh_from_db()
        parse_file2.refresh_from_db()
        assert parse_file.status == 'cancelled'
        assert parse_file2.status == 'cancelled'

