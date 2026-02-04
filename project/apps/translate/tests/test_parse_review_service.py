"""
ParseReviewService 服务层测试
"""
import pytest
import time
import json
from unittest.mock import patch, MagicMock
from django.core.cache import cache

from project.apps.translate.services.parse_review_service import ParseReviewService


@pytest.mark.django_db
class TestParseReviewService:
    """ParseReviewService 服务层测试"""
    
    def setup_method(self):
        """设置测试环境"""
        # 清理缓存
        cache.clear()
    
    def test_save_parse_result(self, mock_parse_result_data):
        """测试保存解析结果到 Redis"""
        file_id = 1
        result = ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        assert result is True
        
        # 验证缓存已保存
        cached_data = ParseReviewService.get_parse_result(file_id)
        assert cached_data is not None
        assert cached_data['file_id'] == file_id
        assert len(cached_data['formatted_data']) == 2
        
        # 验证 edited_formatted 字段自动初始化
        for entry in cached_data['formatted_data']:
            assert 'edited_formatted' in entry
            assert entry['edited_formatted'] == entry['formatted']
    
    def test_save_parse_result_with_timeout(self, mock_parse_result_data):
        """测试保存解析结果时指定过期时间"""
        file_id = 1
        custom_timeout = 3600  # 1小时
        
        result = ParseReviewService.save_parse_result(file_id, mock_parse_result_data, timeout=custom_timeout)
        
        assert result is True
        
        # 验证缓存已保存
        cached_data = ParseReviewService.get_parse_result(file_id)
        assert cached_data is not None
    
    def test_get_parse_result_exists(self, mock_parse_result_data):
        """测试获取存在的缓存数据"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        result = ParseReviewService.get_parse_result(file_id)
        
        assert result is not None
        assert result['file_id'] == file_id
        assert len(result['formatted_data']) == 2
    
    def test_get_parse_result_not_exists(self):
        """测试获取不存在的缓存（返回 None）"""
        file_id = 999
        
        result = ParseReviewService.get_parse_result(file_id)
        
        assert result is None
    
    def test_get_parse_result_json_string(self, mock_parse_result_data):
        """测试处理 JSON 字符串格式的缓存数据"""
        file_id = 1
        cache_key = ParseReviewService._get_cache_key(file_id)
        
        # 模拟缓存后端返回字符串格式
        json_data = json.dumps(mock_parse_result_data)
        cache.set(cache_key, json_data, timeout=3600)
        
        result = ParseReviewService.get_parse_result(file_id)
        
        assert result is not None
        assert result['file_id'] == file_id
    
    def test_get_parse_result_json_decode_error(self):
        """测试处理 JSON 解析失败的情况"""
        file_id = 1
        cache_key = ParseReviewService._get_cache_key(file_id)
        
        # 设置无效的 JSON 字符串
        cache.set(cache_key, 'invalid json{', timeout=3600)
        
        result = ParseReviewService.get_parse_result(file_id)
        
        # 应该返回 None（因为 JSON 解析失败）
        assert result is None
    
    def test_update_entry_formatted(self, mock_parse_result_data):
        """测试更新单条记录的 formatted 和 edited_formatted"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        uuid = 'entry-1'
        new_formatted = '2025-01-20 * "Updated" "Transaction"\n    Expenses:Updated  150.00 CNY\n    Assets:Test  -150.00 CNY\n'
        
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is True
        
        # 验证缓存已更新
        cached_data = ParseReviewService.get_parse_result(file_id)
        updated_entry = next((e for e in cached_data['formatted_data'] if e['uuid'] == uuid), None)
        
        assert updated_entry is not None
        assert updated_entry['formatted'] == new_formatted
        assert updated_entry['edited_formatted'] == new_formatted  # 应该同时更新
    
    def test_update_entry_formatted_cache_not_exists(self):
        """测试更新时缓存不存在的情况"""
        file_id = 999
        uuid = 'entry-1'
        new_formatted = 'test formatted'
        
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is False
    
    def test_update_entry_formatted_uuid_not_found(self, mock_parse_result_data):
        """测试更新时 UUID 不存在的情况"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        uuid = 'non-existent-uuid'
        new_formatted = 'test formatted'
        
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is False
    
    def test_update_entry_edited_formatted(self, mock_parse_result_data):
        """测试更新单条记录的 edited_formatted"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        uuid = 'entry-1'
        new_edited_formatted = '2025-01-20 * "Edited" "Transaction"\n    Expenses:Edited  150.00 CNY\n    Assets:Test  -150.00 CNY\n'
        
        result = ParseReviewService.update_entry_edited_formatted(file_id, uuid, new_edited_formatted)
        
        assert result is True
        
        # 验证缓存已更新
        cached_data = ParseReviewService.get_parse_result(file_id)
        updated_entry = next((e for e in cached_data['formatted_data'] if e['uuid'] == uuid), None)
        
        assert updated_entry is not None
        assert updated_entry['edited_formatted'] == new_edited_formatted
        # formatted 字段应该不受影响
        assert updated_entry['formatted'] != new_edited_formatted
    
    def test_update_entry_edited_formatted_cache_not_exists(self):
        """测试更新 edited_formatted 时缓存不存在的情况"""
        file_id = 999
        uuid = 'entry-1'
        new_edited_formatted = 'test formatted'
        
        result = ParseReviewService.update_entry_edited_formatted(file_id, uuid, new_edited_formatted)
        
        assert result is False
    
    def test_get_final_result(self, mock_parse_result_data):
        """测试返回使用 edited_formatted 的结果"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        # 修改一个条目的 edited_formatted
        uuid = 'entry-1'
        new_edited_formatted = '2025-01-20 * "Edited" "Transaction"\n    Expenses:Edited  150.00 CNY\n    Assets:Test  -150.00 CNY\n'
        ParseReviewService.update_entry_edited_formatted(file_id, uuid, new_edited_formatted)
        
        result = ParseReviewService.get_final_result(file_id)
        
        assert result is not None
        assert len(result) == 2
        
        # 验证第一个条目使用 edited_formatted
        entry1 = next((e for e in result if e['uuid'] == uuid), None)
        assert entry1 is not None
        assert entry1['formatted'] == new_edited_formatted.rstrip()
        
        # 验证去除末尾换行符
        for entry in result:
            assert not entry['formatted'].endswith('\n')
    
    def test_get_final_result_cache_not_exists(self):
        """测试获取最终结果时缓存不存在的情况"""
        file_id = 999
        
        result = ParseReviewService.get_final_result(file_id)
        
        assert result is None
    
    def test_get_final_result_strips_trailing_newlines(self, mock_parse_result_data):
        """测试去除末尾换行符"""
        file_id = 1
        # 添加末尾换行符
        mock_parse_result_data['formatted_data'][0]['edited_formatted'] += '\n\n'
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        result = ParseReviewService.get_final_result(file_id)
        
        assert result is not None
        for entry in result:
            assert not entry['formatted'].endswith('\n')
    
    def test_delete_parse_result(self, mock_parse_result_data):
        """测试删除缓存数据"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        # 验证缓存存在
        assert ParseReviewService.get_parse_result(file_id) is not None
        
        result = ParseReviewService.delete_parse_result(file_id)
        
        assert result is True
        
        # 验证缓存已删除
        assert ParseReviewService.get_parse_result(file_id) is None
    
    def test_delete_parse_result_not_exists(self):
        """测试删除不存在的缓存"""
        file_id = 999
        
        result = ParseReviewService.delete_parse_result(file_id)
        
        # 删除不存在的缓存应该返回 True（幂等操作）
        assert result is True
    
    @patch('project.apps.translate.services.parse_review_service.cache')
    def test_cache_ttl_fallback_when_ttl_not_supported(self, mock_cache, mock_parse_result_data):
        """测试当 cache.ttl() 方法不存在时，使用默认超时时间"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        # 模拟 ttl 方法抛出 AttributeError
        mock_cache.ttl.side_effect = AttributeError("'RedisCache' object has no attribute 'ttl'")
        
        uuid = 'entry-1'
        new_formatted = 'test formatted'
        
        # 应该使用默认超时时间，不会抛出异常
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is True
    
    @patch('project.apps.translate.services.parse_review_service.cache')
    def test_cache_ttl_fallback_when_ttl_returns_none(self, mock_cache, mock_parse_result_data):
        """测试当 cache.ttl() 返回 None 时，使用默认超时时间"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        # 模拟 ttl 返回 None
        mock_cache.ttl.return_value = None
        
        uuid = 'entry-1'
        new_formatted = 'test formatted'
        
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is True
    
    @patch('project.apps.translate.services.parse_review_service.cache')
    def test_cache_ttl_fallback_when_ttl_returns_negative(self, mock_cache, mock_parse_result_data):
        """测试当 cache.ttl() 返回负数时，使用默认超时时间"""
        file_id = 1
        ParseReviewService.save_parse_result(file_id, mock_parse_result_data)
        
        # 模拟 ttl 返回负数
        mock_cache.ttl.return_value = -1
        
        uuid = 'entry-1'
        new_formatted = 'test formatted'
        
        result = ParseReviewService.update_entry_formatted(file_id, uuid, new_formatted)
        
        assert result is True

