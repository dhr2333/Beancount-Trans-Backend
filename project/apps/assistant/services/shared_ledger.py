"""共享账本绑定：令牌校验、绑定增删、可用性解析与账本选项构建。"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.utils import timezone

from project.apps.assistant.models import SharedLedgerBinding
from project.apps.authentication.models import PersonalAccessToken

from .schema_provider import ledger_keys_for

logger = logging.getLogger(__name__)

REQUIRED_SCOPE = 'ledger:read'
DEFAULT_MAX_SHARED_LEDGERS = 3
LAST_USED_THROTTLE_SECONDS = 60
MAX_ALIAS_LENGTH = 64
RESERVED_ALIAS = 'self'


class TokenInvalidError(ValueError):
    """令牌无法用于共享账本绑定（携带面向用户的中文提示）。"""


def get_max_shared_ledgers() -> int:
    """共享账本数量上限（默认 3）。"""
    return int(getattr(settings, 'ASSISTANT_MAX_SHARED_LEDGERS', DEFAULT_MAX_SHARED_LEDGERS))


def normalize_aliases(aliases) -> list[str]:
    """规整别名列表：去空白、丢弃空项、忽略大小写去重（保留首次出现的大小写）。

    空列表合法（表示不带别名，改用来源用户名标识）。超长或保留值会抛错。
    """
    if not aliases:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in aliases:
        alias = str(raw).strip()
        if not alias:
            continue
        lowered = alias.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(alias)
    for alias in normalized:
        if len(alias) > MAX_ALIAS_LENGTH:
            raise TokenInvalidError(f'别名最长为 {MAX_ALIAS_LENGTH} 个字符')
        if alias.lower() == RESERVED_ALIAS:
            raise TokenInvalidError(f'别名不能使用保留值 {RESERVED_ALIAS}')
    return normalized


def bind_by_token(
    recipient: User,
    raw_token: str,
    aliases=None,
) -> SharedLedgerBinding:
    """用对方的个人访问令牌为 recipient 建立共享账本绑定。

    明文令牌仅用于校验，绝不写库或落日志。别名可选、可多个。
    """
    token = PersonalAccessToken.authenticate(raw_token)
    if token is None:
        raise TokenInvalidError('令牌无效或已失效')

    if REQUIRED_SCOPE not in token.scope_list:
        raise TokenInvalidError('该令牌不具备账本只读权限')

    alias_list = normalize_aliases(aliases)

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

    existing_owner_ids = {
        binding.token.user_id
        for binding in SharedLedgerBinding.objects
        .filter(recipient=recipient)
        .select_related('token')
    }
    if token.user_id not in existing_owner_ids:
        max_n = get_max_shared_ledgers()
        usable_owners = {
            binding.token.user_id
            for binding in list_bindings(recipient)
            if binding.is_usable()
        }
        if len(usable_owners) >= max_n:
            raise TokenInvalidError(f'最多绑定 {max_n} 个共享账本，请先解除一个')

    if alias_list:
        other_bindings = (
            SharedLedgerBinding.objects
            .filter(recipient=recipient)
            .exclude(token=token)
        )
        for binding in other_bindings:
            existing_aliases = {str(a).lower() for a in (binding.aliases or [])}
            for alias in alias_list:
                if alias.lower() in existing_aliases:
                    raise TokenInvalidError(
                        f'别名「{alias}」已被其他共享账本使用，请换一个'
                    )

    binding, created = SharedLedgerBinding.objects.get_or_create(
        recipient=recipient,
        token=token,
        defaults={'aliases': alias_list},
    )
    if not created:
        binding.aliases = alias_list
        binding.save(update_fields=['aliases'])
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


def has_usable_shared_ledger(recipient: User) -> bool:
    """recipient 是否存在可用的共享账本绑定（只读检查，不更新 last_used_at）。"""
    return any(binding.is_usable() for binding in list_bindings(recipient))


def usable_binding_ids(recipient: User) -> list[int]:
    """该接收方全部可用绑定的 id（只读，不更新 last_used_at）。

    顺序沿用 SharedLedgerBinding.Meta.ordering（['-created']，最新在前）。
    """
    return [binding.id for binding in list_bindings(recipient) if binding.is_usable()]


def effective_binding_ids(recipient: User, requested: list[int] | None) -> list[int]:
    """把请求参数归一化为实际纳入的绑定 id 列表。

    requested=None → 全部可用（超出上限只取前 N，默认永不报错）；
    requested=[] → 空（仅本人账本）；否则按传入列表（一律转为 int）。
    """
    if requested is None:
        max_n = get_max_shared_ledgers()
        ids = usable_binding_ids(recipient)
        if len(ids) > max_n:
            logger.warning(
                '可用共享账本绑定数 %d 超过上限 %d，仅取前 %d 个',
                len(ids),
                max_n,
                max_n,
            )
        return ids[:max_n]
    return [int(i) for i in requested]


def bindings_with_usability(recipient: User) -> list[dict]:
    """序列化绑定列表，附带可用性判定所需的字段。"""
    rows = []
    for binding in list_bindings(recipient):
        rows.append({
            'id': binding.id,
            'owner_username': binding.token.user.username,
            'aliases': list(binding.aliases or []),
            'usable': binding.is_usable(),
            'expires_at': binding.token.expires_at,
            'last_used_at': binding.last_used_at,
            'created': binding.created,
        })
    return rows


def resolve_shared_ledgers(recipient: User, binding_ids) -> list[dict]:
    """把绑定的 id 列表解析成可用的共享账本（去重保序，忽略非法 id）。"""
    bindings = _usable_bindings(recipient, binding_ids)
    if not bindings:
        return []

    now = timezone.now()
    ledgers: list[dict] = []
    seen: set[int] = set()
    for binding in bindings:
        _touch_last_used(binding, now)
        owner = binding.token.user
        if owner.id in seen:
            continue
        seen.add(owner.id)
        ledgers.append({
            'binding_id': binding.id,
            'aliases': list(binding.aliases or []),
            'owner': owner,
        })
    return ledgers


def build_ledger_options(recipient: User, binding_ids) -> list[dict]:
    """构建账本选项：首项恒为 self，其后为可用的共享账本（key 取首个可用标识）。"""
    options: list[dict] = [{'key': 'self', 'label': '我的账本'}]
    for item in resolve_shared_ledgers(recipient, binding_ids):
        keys = ledger_keys_for(item)
        if item.get('aliases'):
            label = f'{keys[0]}（{item["owner"].username}）'
        else:
            label = f'{item["owner"].username} 的账本'
        options.append({
            'key': keys[0],
            'keys': keys,
            'label': label,
            'binding_id': item['binding_id'],
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
