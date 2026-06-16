from django.contrib.auth.models import User

from project.apps.account.models import Account


class BatchUpdateMappingError(Exception):
    """批量更新映射账户时的业务错误"""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def batch_update_mapping_accounts(
    *,
    user: User,
    model,
    mapping_ids: list,
    account_id: int,
    account_fk_name: str,
    mapping_label: str,
) -> int:
    """批量将映射的账户外键更新为指定账户。"""
    mappings = model.objects.filter(id__in=mapping_ids, owner=user)
    if mappings.count() != len(mapping_ids):
        raise BatchUpdateMappingError(f"部分{mapping_label}不存在或无权限访问")

    try:
        Account.objects.get(id=account_id, owner=user)
    except Account.DoesNotExist:
        raise BatchUpdateMappingError("指定的账户不存在或无权限访问")

    return mappings.update(**{account_fk_name: account_id})
