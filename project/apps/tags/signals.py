import logging

from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from project.apps.tags.models import Tag, TagTemplate

logger = logging.getLogger(__name__)


def tag_exists_for_user(user, tag_path: str) -> bool:
    """检查用户是否已有指定完整路径的标签。"""
    tag_path = tag_path.strip()
    if not tag_path:
        return False

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
            return False
    return True


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
