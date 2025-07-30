import os

from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from project.apps.account.models import Account
from project.apps.account.serializers import AccountSerializer


class AccountViewSet(ModelViewSet):
    """
    list:
    返回账本账户列表数据
    create:
    创建一条新的账本账户数据
    retrieve:
    返回账本账户详情数据
    update:
    更新指定条目账本账户
    delete:
    删除指定账本账户条目
    """
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def perform_create(self, serializer):
        if Account.objects.filter(owner_id=self.request.user, account=self.request.data["account"]).exists():
            raise ValidationError("Account already exists.")

        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'Beancount-Trans-Assets', 'account', 'integration.bean')
        with open(path, 'a', encoding='utf-8') as file:
            data = serializer.validated_data
            output = f"{data['date']} {data['status']} {data['account']} {data['currency']} ; {data['note']}\n"
            file.write(output)
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if Account.objects.filter(owner_id=self.request.user, account=self.request.data["account"]).exclude(
                id=instance.id).exists():
            raise ValidationError("Account already exists.")
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        pass
