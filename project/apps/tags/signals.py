import logging

from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from project.apps.tags.models import Tag, TagTemplate

logger = logging.getLogger(__name__)


def get_tag_by_path_for_user(user, tag_path: str):
    """按完整路径获取用户标签，不存在时返回 None。"""
    tag_path = tag_path.strip()
    if not tag_path:
        return None

    parts = tag_path.split('/')
    current = None
    for part in parts:
        if current is None:
            current = Tag.objects.filter(
                name=part,
                parent__isnull=True,
                owner=user,
            ).first()
        else:
            current = Tag.objects.filter(
                name=part,
                parent=current,
                owner=user,
            ).first()
        if current is None:
            return None
    return current


def tag_exists_for_user(user, tag_path: str) -> bool:
    """检查用户是否已有指定完整路径的标签。"""
    return get_tag_by_path_for_user(user, tag_path) is not None


def resolve_user_tags_by_paths(user, tag_paths) -> list:
    """将标签路径列表解析为用户 Tag 实例，跳过不存在的路径。"""
    if not tag_paths:
        return []

    resolved = []
    for tag_path in tag_paths:
        if not isinstance(tag_path, str):
            continue
        tag_path = tag_path.strip()
        if not tag_path:
            continue
        tag = get_tag_by_path_for_user(user, tag_path)
        if tag is None:
            logger.warning("用户 %s 缺少标签 %s，映射关联已跳过", user.username, tag_path)
            continue
        resolved.append(tag)
    return resolved


def apply_tags_to_mapping(mapping, user, tag_paths) -> None:
    """为映射对象设置标签（按路径解析）。"""
    tags = resolve_user_tags_by_paths(user, tag_paths)
    if tags:
        mapping.tags.set(tags)


def apply_official_tag_templates(user):
    """应用官方标签模板到用户（合并模式：跳过已存在的路径）。返回新创建的标签数量。"""
    official_templates = TagTemplate.objects.filter(is_official=True)
    logger.info("为用户 %s 应用 %s 个官方标签模板", user.username, official_templates.count())

    created_count = 0
    for template in official_templates:
        try:
            for item in template.items.all().order_by('tag_path'):
                tag_path = (item.tag_path or '').strip()
                if not tag_path:
                    continue
                if tag_exists_for_user(user, tag_path):
                    logger.debug("为用户 %s 跳过已存在标签: %s", user.username, tag_path)
                    continue

                tag = Tag(
                    name=tag_path,
                    owner=user,
                    enable=item.enable,
                    description=(item.description or '').strip(),
                )
                tag.save()
                created_count += 1
                logger.debug("为用户 %s 创建标签: %s", user.username, tag_path)
        except Exception as exc:
            logger.error("应用标签模板 %s 失败: %s", template.name, exc)

    return created_count


@receiver(user_signed_up)
def apply_official_tag_templates_on_signup(sender, request, user, **kwargs):
    """用户注册时自动应用官方标签模板。"""
    apply_official_tag_templates(user)
