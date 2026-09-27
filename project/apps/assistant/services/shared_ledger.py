"""共享账本绑定：令牌校验、绑定增删、可用性解析与账本选项构建。"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils import timezone

from project.apps.assistant.models import SharedLedgerBinding
from project.apps.authentication.models import PersonalAccessToken

from .fava_url import read_ledger_title

REQUIRED_SCOPE = 'ledger:read'
DEFAULT_MAX_SHARED_LEDGERS = 3
LAST_USED_THROTTLE_SECONDS = 60


class TokenInvalidError(ValueError):
    """令牌无法用于共享账本绑定（携带面向用户的中文提示）。"""


def get_max_shared_ledgers() -> int:
    """共享账本数量上限（默认 3）。"""
    return int(getattr(settings, 'ASSISTANT_MAX_SHARED_LEDGERS', DEFAULT_MAX_SHARED_LEDGERS))


def bind_by_token(recipient: User, raw_token: str, label: str = '') -> SharedLedgerBinding:
    """用对方的个人访问令牌为 recipient 建立共享账本绑定。

    明文令牌仅用于校验，绝不写库或落日志。
    """
    token = PersonalAccessToken.authenticate(raw_token)
    if token is None:
        raise TokenInvalidError('令牌无效或已失效')

    if REQUIRED_SCOPE not in token.scope_list:
        raise TokenInvalidError('该令牌不具备账本只读权限')

    if token.user_id == recipient.id:
        raise TokenInvalidError('不能绑定自己的账本')

    existing_bindings = (
        SharedLedgerBinding.objects
        .filter(recipient=recipient, token__user_id=token.user_id)
        .select_related('token', 'token__user')
    )
    for binding in existing_bindings:
        if binding.token_id != token.id and binding.is_usable():
            raise TokenInvalidError('已绑定该用户的账本，无需重复添加')

    binding, created = SharedLedgerBinding.objects.get_or_create(
        recipient=recipient,
        token=token,
        defaults={'label': label},
    )
    if not created and label:
        binding.label = label
        binding.save(update_fields=['label'])
    return binding


def unbind(recipient: User, binding_id) -> None:
    """解除 recipient 自己的绑定；不属于 recipient 时抛 DoesNotExist。"""
    binding = SharedLedgerBinding.objects.get(id=binding_id, recipient=recipient)
    binding.delete()


def list_bindings(recipient: User) -> QuerySet:
    """recipient 的全部绑定（含令牌与令牌所属用户）。"""
    return (
        SharedLedgerBinding.objects
        .filter(recipient=recipient)
        .select_related('token', 'token__user')
    )


def bindings_with_usability(recipient: User) -> list[dict]:
    """序列化绑定列表，附带可用性判定所需的字段。"""
    rows = []
    for binding in list_bindings(recipient):
        rows.append({
            'id': binding.id,
            'owner_username': binding.token.user.username,
            'label': binding.label or '',
            'usable': binding.is_usable(),
            'expires_at': binding.token.expires_at,
            'last_used_at': binding.last_used_at,
            'created': binding.created,
        })
    return rows


def resolve_shared_owners(recipient: User, binding_ids) -> list[User]:
    """把绑定的 id 列表解析成可用令牌所属用户（去重保序，忽略非法 id）。"""
    bindings = _usable_bindings(recipient, binding_ids)
    if not bindings:
        return []

    now = timezone.now()
    owners: list[User] = []
    seen: set[int] = set()
    for binding in bindings:
        _touch_last_used(binding, now)
        owner = binding.token.user
        if owner.id in seen:
            continue
        seen.add(owner.id)
        owners.append(owner)
    return owners


def build_ledger_options(recipient: User, binding_ids) -> list[dict]:
    """构建账本选项：首项恒为 self，其后为可用的共享账本。"""
    options = [{'key': 'self', 'label': '我的账本'}]
    seen: set[int] = set()
    for binding in _usable_bindings(recipient, binding_ids):
        owner = binding.token.user
        if owner.id in seen:
            continue
        seen.add(owner.id)
        label = binding.label or read_ledger_title(owner) or f'{owner.username} 的账本'
        options.append({
            'key': owner.username,
            'label': label,
            'binding_id': binding.id,
        })
    return options


def _sanitize_binding_ids(binding_ids) -> list[int]:
    ids: list[int] = []
    for value in binding_ids or []:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _usable_bindings(recipient: User, binding_ids) -> list[SharedLedgerBinding]:
    ids = _sanitize_binding_ids(binding_ids)
    if not ids:
        return []
    bindings = (
        SharedLedgerBinding.objects
        .filter(id__in=ids, recipient=recipient)
        .select_related('token', 'token__user')
    )
    return [binding for binding in bindings if binding.is_usable()]


def _touch_last_used(binding: SharedLedgerBinding, now=None) -> None:
    """按 60 秒节流更新绑定的 last_used_at。"""
    now = now or timezone.now()
    last_used = binding.last_used_at
    if last_used is not None and (now - last_used).total_seconds() < LAST_USED_THROTTLE_SECONDS:
        return
    SharedLedgerBinding.objects.filter(pk=binding.pk).update(last_used_at=now)
    binding.last_used_at = now
