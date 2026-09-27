"""共享账本绑定服务层测试：令牌校验、绑定增删、可用性解析与账本选项。"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from project.apps.assistant.models import SharedLedgerBinding
from project.apps.assistant.services.shared_ledger import (
    TokenInvalidError,
    bind_by_token,
    bindings_with_usability,
    build_ledger_options,
    resolve_shared_owners,
    unbind,
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

        binding = bind_by_token(user, raw_token, label='家庭账本')

        assert binding.recipient_id == user.id
        assert binding.token_id == token.id
        assert binding.owner == owner
        assert binding.is_usable() is True
        assert binding.label == '家庭账本'
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    @pytest.mark.parametrize('raw_token', ['not-a-token', ''])
    def test_bind_invalid_raw_token(self, user, raw_token):
        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token)

    def test_bind_deleted_token_record(self, user, owner):
        token, raw_token = _issue(owner)
        token.delete()

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token)

    def test_bind_revoked_token(self, user, owner):
        token, raw_token = _issue(owner)
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token)

    def test_bind_expired_token(self, user, owner):
        token, raw_token = _issue(
            owner, expires_at=timezone.now() - timedelta(days=1)
        )

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token)

    def test_bind_token_without_required_scope(self, user, owner):
        _token, raw_token = _issue(owner, scopes='other')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token)

        assert '权限' in str(exc_info.value)

    def test_bind_inactive_owner(self, user, owner):
        _token, raw_token = _issue(owner)
        owner.is_active = False
        owner.save(update_fields=['is_active'])

        with pytest.raises(TokenInvalidError):
            bind_by_token(user, raw_token)

    def test_bind_own_token(self, user):
        _token, raw_token = _issue(user, '自己的令牌')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw_token)

        assert '自己' in str(exc_info.value)

    def test_bind_duplicate_owner_rejected(self, user, owner):
        _token1, raw1 = _issue(owner, '第一枚')
        bind_by_token(user, raw1)
        _token2, raw2 = _issue(owner, '第二枚')

        with pytest.raises(TokenInvalidError) as exc_info:
            bind_by_token(user, raw2)

        assert '重复' in str(exc_info.value)
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1

    def test_rebind_same_token_updates_label(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, label='旧备注')

        updated = bind_by_token(user, raw_token, label='新备注')

        assert updated.id == binding.id
        assert updated.label == '新备注'
        assert SharedLedgerBinding.objects.filter(recipient=user).count() == 1


@pytest.mark.django_db
class TestUnbind:
    def test_unbind_own_binding(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token)

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
        binding = bind_by_token(user, raw_token, label='共享')

        rows = bindings_with_usability(user)

        assert len(rows) == 1
        row = rows[0]
        assert row['id'] == binding.id
        assert row['owner_username'] == owner.username
        assert row['label'] == '共享'
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
class TestResolveSharedOwners:
    def test_returns_owner_for_usable_binding(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token)

        assert resolve_shared_owners(user, [binding.id]) == [owner]

    @pytest.mark.parametrize('binding_ids', [[], None])
    def test_empty_ids_returns_empty_list(self, user, binding_ids):
        assert resolve_shared_owners(user, binding_ids) == []

    def test_other_recipient_binding_ignored(self, user, owner):
        token, _raw = _issue(user, '令牌')
        other_binding = SharedLedgerBinding.objects.create(
            recipient=owner, token=token
        )

        assert resolve_shared_owners(user, [other_binding.id]) == []

    def test_nonexistent_id_ignored(self, user):
        assert resolve_shared_owners(user, [999999]) == []

    @pytest.mark.parametrize('mutate', ['revoked', 'expired'])
    def test_unusable_token_excluded(self, user, owner, mutate):
        token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token)
        if mutate == 'revoked':
            token.revoked_at = timezone.now()
            token.save(update_fields=['revoked_at'])
        else:
            token.expires_at = timezone.now() - timedelta(days=1)
            token.save(update_fields=['expires_at'])

        assert resolve_shared_owners(user, [binding.id]) == []

    def test_duplicate_owners_deduplicated(self, user, owner):
        token1, _raw1 = _issue(owner, '令牌一')
        token2, _raw2 = _issue(owner, '令牌二')
        binding1 = SharedLedgerBinding.objects.create(recipient=user, token=token1)
        binding2 = SharedLedgerBinding.objects.create(recipient=user, token=token2)

        owners = resolve_shared_owners(user, [binding1.id, binding2.id])

        assert owners == [owner]

    def test_last_used_at_updated_with_throttle(self, user, owner):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token)

        resolve_shared_owners(user, [binding.id])
        binding.refresh_from_db()
        first_used = binding.last_used_at
        assert first_used is not None

        # 60 秒内的第二次解析不应刷新
        resolve_shared_owners(user, [binding.id])
        binding.refresh_from_db()
        assert binding.last_used_at == first_used

        # 人为把 last_used_at 调到 60 秒前，应再次刷新
        old_used = timezone.now() - timedelta(seconds=120)
        SharedLedgerBinding.objects.filter(pk=binding.pk).update(last_used_at=old_used)
        resolve_shared_owners(user, [binding.id])
        binding.refresh_from_db()
        assert binding.last_used_at > old_used


@pytest.mark.django_db
class TestBuildLedgerOptions:
    def test_first_option_is_self(self, user, assets_dir):
        assert build_ledger_options(user, []) == [
            {'key': 'self', 'label': '我的账本'},
        ]

    def test_shared_entry_uses_binding_label(self, user, owner, assets_dir):
        _token, raw_token = _issue(owner)
        binding = bind_by_token(user, raw_token, label='家庭账本')

        options = build_ledger_options(user, [binding.id])

        assert options[0] == {'key': 'self', 'label': '我的账本'}
        assert options[1] == {
            'key': owner.username,
            'label': '家庭账本',
            'binding_id': binding.id,
        }

    def test_shared_entry_falls_back_to_ledger_title(self, user, owner, assets_dir):
        owner_dir = assets_dir / owner.username
        owner_dir.mkdir(parents=True)
        (owner_dir / 'main.bean').write_text(
            'option "title" "家庭账本"\n', encoding='utf-8'
        )
        token, _raw = _issue(owner)
        binding = SharedLedgerBinding.objects.create(recipient=user, token=token)

        options = build_ledger_options(user, [binding.id])

        assert options[1]['label'] == '家庭账本'
        assert options[1]['key'] == owner.username
        assert options[1]['binding_id'] == binding.id

    def test_shared_entry_falls_back_to_default_label(self, user, owner, assets_dir):
        token, _raw = _issue(owner)
        binding = SharedLedgerBinding.objects.create(recipient=user, token=token)

        options = build_ledger_options(user, [binding.id])

        assert options[1]['label'] == f'{owner.username}的账本'

    def test_shared_entry_falls_back_to_username_label(
        self, user, owner, monkeypatch,
    ):
        # read_ledger_title 恒返回非空串，仅在返回空串时才会走到 username 兜底分支
        monkeypatch.setattr(
            'project.apps.assistant.services.shared_ledger.read_ledger_title',
            lambda _user: '',
        )
        token, _raw = _issue(owner)
        binding = SharedLedgerBinding.objects.create(recipient=user, token=token)

        options = build_ledger_options(user, [binding.id])

        assert options[1]['label'] == f'{owner.username} 的账本'
