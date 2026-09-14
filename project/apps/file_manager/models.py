# project/apps/file_manager/models.py
import os

from django.db import models
from django.contrib.auth.models import User

class Directory(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='children')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'parent')

    def get_path(self):
        if not self.parent:
            return self.name
        return f"{self.parent.get_path()}/{self.name}"

    def get_relative_path(self):
        """获取相对用户根目录的路径（不包含根目录自身的名称）

        例如：根目录为 "Root"，则 "Root/Test" 返回 "Test"；
        根目录自身返回空字符串 ""。

        Returns:
            str: 以 "/" 分隔的相对路径，根目录返回 ""
        """
        parts = []
        current = self
        # 限制循环次数，防御损坏数据造成的 parent 环
        for _ in range(1000):
            if current.parent is None:
                # 已到达用户根目录，根目录名称不计入相对路径
                break
            parts.append(current.name)
            current = current.parent
        return "/".join(reversed(parts))


class File(models.Model):
    name = models.CharField(max_length=255)
    directory = models.ForeignKey(Directory, on_delete=models.CASCADE, related_name='files')
    storage_name = models.CharField(max_length=1024)
    size = models.BigIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=100)


    class Meta:
        unique_together = ('name', 'directory')

    @property
    def minio_path(self):
        """返回MinIO中的存储路径"""
        return self.storage_name

    def get_bean_dir(self):
        """获取该文件对应的账本子目录（相对于 trans/ 的路径）

        Returns:
            str: 以 "/" 分隔的相对目录，位于根目录下时返回 ""
        """
        return self.directory.get_relative_path()

    def get_bean_relative_path(self):
        """获取该文件对应的账本相对于 trans/ 的相对路径（POSIX 格式）

        Returns:
            str: 如 "Test/202505_alipay.bean"，位于根目录下时为 "202505_alipay.bean"
        """
        base_name = os.path.splitext(self.name)[0]
        bean_dir = self.get_bean_dir()
        if bean_dir:
            return f"{bean_dir}/{base_name}.bean"
        return f"{base_name}.bean"

