"""共享账本绑定服务层测试：令牌校验、绑定增删、可用性解析与账本选项。"""
import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from project.apps.assistant.models import SharedLedgerBinding
from project.apps.assistant.services.shared_ledger import (
    TokenInvalidError,
    bind_by_token,
    bindings_with_usability,
    build_ledger_options,
    effective_binding_ids,
    has_usable_shared_ledger,
    resolve_shared_ledgers,
    unbind,
    usable_binding_ids,
)
from project.apps.authentication.models import PersonalAccessToken

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username='owneruser',
        email='owner@example.com',
        password='testpass123',
    )


@pytest.fixture
def assets_dir(tmp_path, settings, monkeypatch):
    """把资产根目录指向临时目录，隔离 read_ledger_title 的真实文件读取。"""
    monkeypatch.setattr(settings, 'ASSETS_BASE_PATH', tmp_path)
    return tmp_path


def _issue(owner, name='分享账本', **kwargs):
    return PersonalAccessToken.issue(owner, name, **kwargs)


@pytest.mark.django_db
class TestBindByToken:
    def test_bind_success(self, user, owner):
        token, raw_token = _issue(owner, '分享给 B')

        binding = bind_by_token(user, raw_token, ['家庭账本'])

        assert binding.recipient_id == user.id
        assert binding.token_id == token.id
        assert binding.owner == owner
        assert binding.is_usable() is True
        assert binding.aliases == ['家庭账本']
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    def test_bind_multiple_aliases(self, user, owner):
        _token, raw_token = _issue(owner)

        binding = bind_by_token(user, raw_token, ['老婆的账本', '老婆'])

        assert binding.aliases == ['老婆的账本', '老婆']

    @pytest.mark.parametrize('raw_token', ['not-a-token', ''])
    def test_bind_invalid_raw_token(self, user, raw_token):
        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token, ['别名'])

    def test_bind_deleted_token_record(self, user, owner):
        token, raw_token = _issue(owner)
        token.delete()

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token, ['别名'])

    def test_bind_revoked_token(self, user, owner):
        token, raw_token = _issue(owner)
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token, ['别名'])

    def test_bind_expired_token(self, user, owner):
        token, raw_token = _issue(
            owner, expires_at=timezone.now() - timedelta(days=1)
        )

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token, ['别名'])

    def test_bind_token_without_required_scope(self, user, owner):
        _token, raw_token = _issue(owner, scopes='other')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, ['别名'])

        assert '权限' in str(exc_info.value)

    def test_bind_inactive_owner(self, user, owner):
        _token, raw_token = _issue(owner)
        owner.is_active = False
        owner.save(update_fields=['is_active'])

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token, ['别名'])

    def test_bind_own_token(self, user):
        _token, raw_token = _issue(user, '自己的令牌')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, ['别名'])

        assert '自己' in str(exc_info.value)

    def test_bind_duplicate_owner_rejected(self, user, owner):
        _token1, raw1 = _issue(owner, '第一枚')
        bind_by_token(user, raw1, ['账本一'])
        _token2, raw2 = _issue(owner, '第二枚')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw2, ['账本二'])

        assert '重复' in str(exc_info.value)
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    def test_rebind_same_token_replaces_alias_list(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['旧别名'])

        updated = bind_by_token(user, raw_token, ['新别名', '新别名2'])

        assert updated.id == binding.id
        assert updated.aliases == ['新别名', '新别名2']
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    @pytest.mark.parametrize('aliases', [None, [], ['', '   ']])
    def test_bind_without_or_blank_aliases_allowed(self, user, owner, aliases):
        _token, raw_token = _issue(owner)

        binding = bind_by_token(user, raw_token, aliases)

        assert binding.aliases == []

    def test_bind_overlong_alias_rejected(self, user, owner):
        _token, raw_token = _issue(owner)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, ['账本' * 40])

        assert '别名最长为 64 个字符' in str(exc_info.value)

    @pytest.mark.parametrize('reserved', ['self', 'SELF', ' self '])
    def test_bind_reserved_alias_rejected(self, user, owner, reserved):
        _token, raw_token = _issue(owner)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, [reserved])

        assert '别名不能使用保留值 self' in str(exc_info.value)

    def test_bind_aliases_stored_stripped_and_deduped(self, user, owner):
        _token, raw_token = _issue(owner)

        binding = bind_by_token(
            user, raw_token, ['  老婆的账本  ', '老婆的账本', 'FAMILY', 'family']
        )

        assert binding.aliases == ['老婆的账本', 'FAMILY']

    def test_bind_duplicate_alias_for_other_owner_rejected(self, user, owner):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        bind_by_token(user, raw1, ['家庭账本'])
        _token2, raw2 = _issue(other)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw2, ['家庭账本'])

        assert '已被其他共享账本使用' in str(exc_info.value)
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    def test_bind_alias_conflict_is_case_insensitive(self, user, owner):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        bind_by_token(user, raw1, ['Family'])
        _token2, raw2 = _issue(other)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw2, ['family'])

        assert '已被其他共享账本使用' in str(exc_info.value)

    def test_same_alias_allowed_for_different_recipients(self, user, owner):
        other_recipient = User.objects.create_user(username='recipient2', password='x')
        _token, raw_token = _issue(owner)

        first = bind_by_token(user, raw_token, ['家庭账本'])
        second = bind_by_token(other_recipient, raw_token, ['家庭账本'])

        assert first.aliases == ['家庭账本']
        assert second.aliases == ['家庭账本']
        assert first.recipient_id != second.recipient_id

    def test_rebind_alias_collision_with_other_binding_rejected(self, user, owner):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        bind_by_token(user, raw1, ['账本一'])
        _token2, raw2 = _issue(other)
        bind_by_token(user, raw2, ['账本二'])

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw1, ['账本二'])

        assert '已被其他共享账本使用' in str(exc_info.value)
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 2
        binding = SharedLedgerBinding.objects.get(recipient=user, token__user=owner)
        assert binding.aliases == ['账本一']


@pytest.mark.django_db
class TestBindByTokenCap:
    def _bind_owner(self, user, username, alias=''):
        owner = User.objects.create_user(username=username, password='x')
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, [alias] if alias else [])
        return owner, binding

    def test_three_distinct_owners_allowed(self, user):
        for i in range(3):
            self._bind_owner(user, f'capowner{i}')

        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 3

    def test_fourth_distinct_owner_rejected(self, user):
        for i in range(3):
            self._bind_owner(user, f'capowner{i}')
        fourth = User.objects.create_user(username='capowner3', password='x')
        _token, raw_token = _issue(fourth)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, [])

        assert str(exc_info.value) == '最多绑定 3 个共享账本，请先解除一个'
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 3

    @override_settings(ASSISTANT_MAX_SHARED_LEDGERS=1)
    def test_custom_max_rejects_second_owner(self, user):
        self._bind_owner(user, 'capowner0')
        second = User.objects.create_user(username='capowner1', password='x')
        _token, raw_token = _issue(second)

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token, [])

        assert str(exc_info.value) == '最多绑定 1 个共享账本，请先解除一个'
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    def test_same_owner_rebind_allowed_at_cap_when_previous_unusable(self, user):
        owners = []
        for i in range(3):
            owner, _binding = self._bind_owner(user, f'capowner{i}')
            owners.append(owner)
        # 撤销第 3 个 owner 的令牌，使其绑定不可用
        revoked = SharedLedgerBinding.objects.get(
            recipient=user, token__user=owners[2]
        )
        revoked.token.revoked_at = timezone.now()
        revoked.token.save(update_fields=['revoked_at'])
        # 新的第 4 个 owner 绑定，重新达到可用上限
        self._bind_owner(user, 'capowner_extra')
        # 已被撤销的第 3 个 owner 换新令牌重绑：不受上限限制
        _new_token, raw_new = _issue(owners[2])

        rebinding = bind_by_token(user, raw_new, ['第三个账本'])

        assert rebinding.owner == owners[2]

    def test_same_token_repaste_new_alias_allowed_at_cap(self, user):
        raws = []
        for i in range(3):
            owner = User.objects.create_user(username=f'capowner{i}', password='x')
            _token, raw_token = _issue(owner)
            bind_by_token(user, raw_token, [f'账本{i}'])
            raws.append(raw_token)

        rebinding = bind_by_token(user, raws[0], ['新别名'])

        assert rebinding.aliases == ['新别名']
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 3


@pytest.mark.django_db
class TestUnbind:
    def test_unbind_own_binding(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        unbind(user, binding.id)

        assert not SharedLedgerBinding.objects.filter(id=binding.id).exists()

    def test_unbind_other_users_binding_not_allowed(self, user, owner):
        token, _raw = _issue(user, '我的令牌')
        binding = SharedLedgerBinding.objects.create(
            recipient=owner, token=token
        )

        with pytest.raises(SharedLedgerBinding.DoesNotExist):
            unbind(user, binding.id)

        assert SharedLedgerBinding.objects.filter(id=binding.id).exists()


@pytest.mark.django_db
class TestBindingsWithUsability:
    def test_row_contains_expected_fields(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['共享'])

        rows = bindings_with_usability(user)

        assert len(rows) == 1
        row = rows[0]
        assert row['id'] == binding.id
        assert row['owner_username'] == owner.username
        assert row['aliases'] == ['共享']
        assert row['usable'] is True
        assert row['expires_at'] is None

    def test_revoked_token_serialized_unusable_but_present(self, user, owner):
        token, _raw = _issue(owner)
        binding = SharedLedgerBinding.objects.create(recipient=user, token=token)
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])

        rows = bindings_with_usability(user)

        assert [row['id'] for row in rows] == [binding.id]
        assert rows[0]['usable'] is False


@pytest.mark.django_db
class TestHasUsableSharedLedger:
    def test_true_with_usable_binding(self, user, owner):
        _token, raw_token = _issue(owner)
        bind_by_token(user, raw_token, ['家庭账本'])

        assert has_usable_shared_ledger(user) is True

    def test_false_without_binding(self, user):
        assert has_usable_shared_ledger(user) is False

    @pytest.mark.parametrize('mutate', ['revoked', 'expired'])
    def test_false_when_only_token_unusable(self, user, owner, mutate):
        token, raw_token = _issue(owner)
        bind_by_token(user, raw_token, ['家庭账本'])
        if mutate == 'revoked':
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at'])
        else:
            token.expires_at = timezone.now() - timedelta(days=1)
            token.save(update_fields=['expires_at'])

        assert has_usable_shared_ledger(user) is False

    def test_false_when_owner_inactive(self, user, owner):
        _token, raw_token = _issue(owner)
        bind_by_token(user, raw_token, ['家庭账本'])
        owner.is_active = False
        owner.save(update_fields=['is_active'])

        assert has_usable_shared_ledger(user) is False

    def test_does_not_touch_last_used_at(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])
        assert binding.last_used_at is None

        has_usable_shared_ledger(user)

        binding.refresh_from_db()
        assert binding.last_used_at is None

        old_used = timezone.now() - timedelta(seconds=120)
        SharedLedgerBinding.objects.filter(pk=binding.pk).update(last_used_at=old_used)

        has_usable_shared_ledger(user)

        binding.refresh_from_db()
        assert binding.last_used_at == old_used


@pytest.mark.django_db
class TestUsableBindingIds:
    def test_returns_usable_ids_newest_first_skipping_unusable(self, user):
        older_owner = User.objects.create_user(username='olderowner', password='x')
        newer_owner = User.objects.create_user(username='newerowner', password='x')
        revoked_owner = User.objects.create_user(username='revokedowner', password='x')
        _t1, raw1 = _issue(older_owner)
        _t2, raw2 = _issue(newer_owner)
        revoked_token, raw3 = _issue(revoked_owner)
        older = bind_by_token(user, raw1, ['旧'])
        newer = bind_by_token(user, raw2, ['新'])
        bind_by_token(user, raw3, ['撤销'])
        revoked_token.revoked_at = timezone.now()
        revoked_token.save(update_fields=['revoked_at'])

        # Meta.ordering = ['-created']：最新绑定的 id 在前，不可用绑定被跳过
        assert usable_binding_ids(user) == [newer.id, older.id]

    def test_does_not_touch_last_used_at(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])
        assert binding.last_used_at is None

        usable_binding_ids(user)

        binding.refresh_from_db()
        assert binding.last_used_at is None


@pytest.mark.django_db
class TestEffectiveBindingIds:
    def test_none_returns_all_usable_newest_first(self, user):
        first_owner = User.objects.create_user(username='effowner1', password='x')
        second_owner = User.objects.create_user(username='effowner2', password='x')
        _t1, raw1 = _issue(first_owner)
        _t2, raw2 = _issue(second_owner)
        first = bind_by_token(user, raw1, ['一'])
        second = bind_by_token(user, raw2, ['二'])

        assert effective_binding_ids(user, None) == [second.id, first.id]

    def test_none_truncated_to_max_with_warning(self, user, caplog):
        first_owner = User.objects.create_user(username='effowner1', password='x')
        second_owner = User.objects.create_user(username='effowner2', password='x')
        _t1, raw1 = _issue(first_owner)
        _t2, raw2 = _issue(second_owner)
        bind_by_token(user, raw1, ['一'])
        second = bind_by_token(user, raw2, ['二'])

        with override_settings(ASSISTANT_MAX_SHARED_LEDGERS=1):
            with caplog.at_level(
                logging.WARNING,
                logger='project.apps.assistant.services.shared_ledger',
            ):
                result = effective_binding_ids(user, None)

        assert result == [second.id]
        assert '超过上限' in caplog.text

    def test_empty_list_returns_empty(self, user, owner):
        _token, raw_token = _issue(owner)
        bind_by_token(user, raw_token, ['家庭账本'])

        assert effective_binding_ids(user, []) == []

    def test_explicit_list_coerced_to_ints(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        assert effective_binding_ids(user, [str(binding.id), 8]) == [binding.id, 8]


@pytest.mark.django_db
class TestResolveSharedLedgers:
    def test_returns_ledger_for_usable_binding(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        ledgers = resolve_shared_ledgers(user, [binding.id])

        assert [item['owner'] for item in ledgers] == [owner]
        assert ledgers[0]['aliases'] == ['家庭账本']
        assert ledgers[0]['binding_id'] == binding.id

    @pytest.mark.parametrize('binding_ids', [[], None])
    def test_empty_ids_returns_empty_list(self, user, binding_ids):
        assert resolve_shared_ledgers(user, binding_ids) == []

    def test_other_recipient_binding_ignored(self, user, owner):
        token, _raw = _issue(user, '令牌')
        other_binding = SharedLedgerBinding.objects.create(
            recipient=owner, token=token, aliases=['别人的账本']
        )

        assert resolve_shared_ledgers(user, [other_binding.id]) == []

    def test_nonexistent_id_ignored(self, user):
        assert resolve_shared_ledgers(user, [999999]) == []

    @pytest.mark.parametrize('mutate', ['revoked', 'expired'])
    def test_unusable_token_excluded(self, user, owner, mutate):
        token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])
        if mutate == 'revoked':
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at'])
        else:
            token.expires_at = timezone.now() - timedelta(days=1)
            token.save(update_fields=['expires_at'])

        assert resolve_shared_ledgers(user, [binding.id]) == []

    def test_duplicate_owners_deduplicated(self, user, owner):
        token1, _raw1 = _issue(owner, '令牌一')
        token2, _raw2 = _issue(owner, '令牌二')
        binding1 = SharedLedgerBinding.objects.create(
            recipient=user, token=token1, aliases=['账本一']
        )
        binding2 = SharedLedgerBinding.objects.create(
            recipient=user, token=token2, aliases=['账本二']
        )

        ledgers = resolve_shared_ledgers(user, [binding1.id, binding2.id])

        assert [item['owner'] for item in ledgers] == [owner]
        assert len(ledgers) == 1
        assert ledgers[0]['aliases'] in (['账本一'], ['账本二'])

    def test_last_used_at_updated_with_throttle(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        resolve_shared_ledgers(user, [binding.id])
        binding.refresh_from_db()
        first_used = binding.last_used_at
        assert first_used is not None

        # 60 秒内的第二次解析不应刷新
        resolve_shared_ledgers(user, [binding.id])
        binding.refresh_from_db()
        assert binding.last_used_at == first_used

        # 人为把 last_used_at 调到 60 秒前，应再次刷新
        old_used = timezone.now() - timedelta(seconds=120)
        SharedLedgerBinding.objects.filter(pk=binding.pk).update(last_used_at=old_used)
        resolve_shared_ledgers(user, [binding.id])
        binding.refresh_from_db()
        assert binding.last_used_at > old_used

    def test_item_exposes_aliases_binding_id_and_owner(self, user, owner):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        _token2, raw2 = _issue(other)
        binding1 = bind_by_token(user, raw1, ['老婆的账本'])
        binding2 = bind_by_token(user, raw2, ['孩子的账本'])

        ledgers = resolve_shared_ledgers(user, [binding1.id, binding2.id])

        by_owner = {item['owner']: item for item in ledgers}
        assert set(by_owner) == {owner, other}
        assert all(set(item) == {'binding_id', 'aliases', 'owner'} for item in ledgers)
        assert by_owner[owner]['binding_id'] == binding1.id
        assert by_owner[owner]['aliases'] == ['老婆的账本']
        assert by_owner[other]['binding_id'] == binding2.id
        assert by_owner[other]['aliases'] == ['孩子的账本']


@pytest.mark.django_db
class TestBuildLedgerOptions:
    def test_first_option_is_self(self, user, assets_dir):
        assert build_ledger_options(user, []) == [
            {'key': 'self', 'label': '我的账本'},
        ]

    def test_shared_entry_uses_binding_aliases(self, user, owner, assets_dir):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        options = build_ledger_options(user, [binding.id])

        assert options[0] == {'key': 'self', 'label': '我的账本'}
        assert options[1] == {
            'key': '家庭账本',
            'keys': ['家庭账本'],
            'label': f'家庭账本（{owner.username}）',
            'binding_id': binding.id,
        }

    def test_shared_entry_key_is_first_alias(self, user, owner, assets_dir):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['老婆的账本', '老婆'])

        options = build_ledger_options(user, [binding.id])

        assert options[1]['key'] == '老婆的账本'
        assert options[1]['keys'] == ['老婆的账本', '老婆']
        assert options[1]['binding_id'] == binding.id

    def test_shared_entry_label_includes_owner_username(self, user, owner, assets_dir):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, ['家庭账本'])

        options = build_ledger_options(user, [binding.id])

        assert options[1]['label'] == f'家庭账本（{owner.username}）'

    def test_shared_entry_without_aliases_uses_owner_username(self, user, owner, assets_dir):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, [])

        options = build_ledger_options(user, [binding.id])

        assert options[1]['key'] == owner.username
        assert options[1]['keys'] == [owner.username]
        assert options[1]['label'] == f'{owner.username} 的账本'
        assert options[1]['binding_id'] == binding.id

    def test_multiple_shared_entries_use_their_aliases(self, user, owner, assets_dir):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        _token2, raw2 = _issue(other)
        binding1 = bind_by_token(user, raw1, ['家庭账本'])
        binding2 = bind_by_token(user, raw2, ['备用账本'])

        options = build_ledger_options(user, [binding1.id, binding2.id])

        assert options[0] == {'key': 'self', 'label': '我的账本'}
        assert {o['key'] for o in options[1:]} == {'家庭账本', '备用账本'}
        assert any(
            o['label'] == f'家庭账本（{owner.username}）' for o in options
        )
        assert any(
            o['label'] == f'备用账本（{other.username}）' for o in options
        )

    def test_touches_each_binding_once(self, user, owner, assets_dir):
        other = User.objects.create_user(username='otheruser', password='x')
        _token1, raw1 = _issue(owner)
        _token2, raw2 = _issue(other)
        binding1 = bind_by_token(user, raw1, ['家庭账本'])
        binding2 = bind_by_token(user, raw2, ['备用账本'])

        with patch(
            'project.apps.assistant.services.shared_ledger._touch_last_used'
        ) as spy:
            options = build_ledger_options(user, [binding1.id, binding2.id])

        assert len(options) == 3
        assert spy.call_count == 2
