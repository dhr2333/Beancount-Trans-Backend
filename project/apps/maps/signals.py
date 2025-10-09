from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import Template
from .views import TemplateViewSet

@receiver(user_signed_up)
def apply_official_templates_on_signup(sender, request, user, **kwargs):
    """用户注册时自动应用官方模板"""
    apply_official_templates(user)

def apply_official_templates(user):
    """应用官方模板到用户"""
    # 获取所有官方模板
    official_templates = Template.objects.filter(is_official=True)

    # 创建一个模拟的视图实例来处理模板应用
    view = TemplateViewSet()
    view.request = type('Request', (), {'user': user})()  # 模拟请求对象

    for template in official_templates:
        # 使用合并方式，跳过冲突
        if template.type == 'expense':
            view._apply_expense_template(template, 'merge', 'skip')
        elif template.type == 'income':
            view._apply_income_template(template, 'merge', 'skip')
        elif template.type == 'assets':
            view._apply_assets_template(template, 'merge', 'skip')
