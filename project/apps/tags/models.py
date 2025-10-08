from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from project.models import BaseModel


class Tag(BaseModel):
    """标签模型"""
    name = models.CharField(max_length=64, help_text="标签名称")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children', help_text="父标签")
    description = models.TextField(blank=True, help_text="标签描述")
    owner = models.ForeignKey(User, related_name='tags', on_delete=models.CASCADE, db_index=True)
    enable = models.BooleanField(default=True, help_text="是否启用")

    class Meta:
        db_table = 'tags_tag'
        unique_together = ['name', 'owner']
        ordering = ['name']
        verbose_name = '标签'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.get_full_path()
    
    def clean(self):
        """验证标签数据"""
        # 检查标签名称是否包含非法字符
        invalid_chars = [' ', '#', '\n', '\r', '\t']
        for char in invalid_chars:
            if char in self.name:
                raise ValidationError(f"标签名称不能包含字符: '{char}'")
        
        # 防止循环引用
        if self.parent:
            current = self.parent
            visited = set([self.id]) if self.id else set()
            while current:
                if current.id in visited:
                    raise ValidationError("检测到循环引用，无法设置父标签")
                visited.add(current.id)
                current = current.parent
    
    def save(self, *args, **kwargs):
        """保存标签时自动处理父标签和状态同步"""
        # 检查enable字段是否发生变化
        enable_changed = False
        name_changed = False
        old_name = None
        
        if self.pk:
            try:
                old_instance = Tag.objects.get(pk=self.pk)
                enable_changed = old_instance.enable != self.enable
                name_changed = old_instance.name != self.name
                if name_changed:
                    old_name = old_instance.name
            except Tag.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # 如果enable状态发生变化，同步更新子标签状态
        if enable_changed and not self.enable:
            self._disable_children()
    
    def _disable_children(self):
        """递归禁用所有子标签"""
        for child in self.children.all():
            if child.enable:
                child.enable = False
                child.save()
    
    def has_children(self):
        """检查是否存在子标签"""
        return self.children.exists()
    
    def get_full_path(self):
        """
        获取标签的完整路径（包含父标签）
        
        Returns:
            str: 标签完整路径，如 "Category/EDUCATION" 或 "Irregular"
        """
        path_parts = []
        current = self
        
        # 向上遍历到根标签
        while current:
            path_parts.insert(0, current.name)
            current = current.parent
        
        # 用斜杠连接
        return '/'.join(path_parts)
    
    def get_all_children(self):
        """
        递归获取所有子标签ID
        
        Returns:
            list: 所有子标签的ID列表（包括子标签的子标签）
        """
        child_ids = []
        for child in self.children.all():
            child_ids.append(child.id)
            child_ids.extend(child.get_all_children())
        return child_ids
    
    def delete_with_children(self, force=False):
        """
        删除标签及其所有子标签
        
        Args:
            force: 是否强制删除（即使有映射关联）
        
        Returns:
            dict: 删除结果
        """
        # 检查是否有子标签
        if self.has_children() and not force:
            raise ValidationError("标签存在子标签，请使用强制删除或先删除子标签")
        
        result = {
            'deleted_tag': {
                'id': self.id,
                'name': self.name,
                'full_path': self.get_full_path()
            },
            'deleted_children_count': 0,
            'affected_mappings': 0
        }
        
        # 统计子标签数量
        if self.has_children():
            children_ids = self.get_all_children()
            result['deleted_children_count'] = len(children_ids)
        
        # TODO: 在Phase 2中，检查和处理映射关联
        # 目前直接删除（CASCADE会自动处理）
        
        self.delete()
        
        return result
