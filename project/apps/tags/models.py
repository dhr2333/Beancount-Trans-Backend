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
        """保存标签时自动创建父标签，并同步状态"""
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

        # 根据标签路径计算父标签：仅当提交完整路径或显式重命名为根标签时更新 parent
        if '/' in self.name:
            parent_tag_path = '/'.join(self.name.split('/')[:-1])
            self.name = self.name.split('/')[-1]
            try:
                new_parent = self._get_tag_by_path(parent_tag_path)
                if new_parent.pk == self.pk:
                    raise ValidationError("标签不能成为自己的父标签")
                if self.parent != new_parent:
                    self.parent = new_parent
            except Tag.DoesNotExist:
                self.parent = self._create_parent_tag(parent_tag_path)
        elif name_changed:
            self.parent = None

        super().save(*args, **kwargs)

        if enable_changed:
            if self.enable:
                self._enable_ancestors()
            else:
                self._disable_children()

    def _get_tag_by_path(self, path):
        """根据完整路径查找标签"""
        if '/' in path:
            parent_path = '/'.join(path.split('/')[:-1])
            leaf_name = path.split('/')[-1]
            parent_tag = self._get_tag_by_path(parent_path)
            return Tag.objects.get(name=leaf_name, parent=parent_tag, owner=self.owner)
        return Tag.objects.get(name=path, parent__isnull=True, owner=self.owner)

    def _create_parent_tag(self, parent_tag_path):
        """递归创建父标签（参考 Account 的实现）"""
        try:
            return self._get_tag_by_path(parent_tag_path)
        except Tag.DoesNotExist:
            parent = Tag(
                name=parent_tag_path,
                owner=self.owner,
                enable=True
            )
            parent.save()
            return parent

    def _enable_ancestors(self):
        """启用所有祖先标签"""
        current = self.parent
        while current:
            if Tag.objects.filter(pk=current.pk, enable=False).update(enable=True):
                current.enable = True
            current = current.parent

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
