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