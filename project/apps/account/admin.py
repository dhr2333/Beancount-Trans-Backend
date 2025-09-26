from django.contrib import admin
from django.utils.html import format_html
# from django.urls import reverse
# from django.utils.safestring import mark_safe
from django.db import models
from django.forms import TextInput

from project.apps.account.models import Account, Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    """货币管理"""
    list_display = ['code', 'name', 'owner', 'created', 'modified']
    list_filter = ['owner', 'created', 'modified']
    search_fields = ['code', 'name', 'owner__username']
    ordering = ['code']
    readonly_fields = ['created', 'modified']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('code', 'name', 'owner')
        }),
        ('时间信息', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """根据用户权限过滤数据"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)
    
    def save_model(self, request, obj, form, change):
        """保存模型时设置属主"""
        if not change:  # 新建时
            obj.owner = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """根据用户权限设置只读字段"""
        readonly_fields = list(self.readonly_fields)
        
        # 非管理员不能修改owner字段
        if not request.user.is_superuser:
            readonly_fields.append('owner')
        
        return readonly_fields
    
    def has_change_permission(self, request, obj=None):
        """检查修改权限"""
        if obj and not request.user.is_superuser:
            return obj.owner == request.user
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """检查删除权限"""
        if obj and not request.user.is_superuser:
            return obj.owner == request.user
        return super().has_delete_permission(request, obj)


class AccountInline(admin.TabularInline):
    """子账户内联编辑"""
    model = Account
    fk_name = 'parent'
    extra = 0
    fields = ['account', 'enable', 'currencies']
    readonly_fields = ['created', 'modified']
    
    def get_queryset(self, request):
        """只显示子账户"""
        qs = super().get_queryset(request)
        return qs.filter(parent__isnull=False)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """账户管理"""
    list_display = [
        'account', 'account_type', 'owner', 'enable', 
        'has_children_display', 'mapping_count_display', 
        'currencies_display', 'created'
    ]
    list_filter = [
        'enable', 'owner', 'created', 'modified',
        ('account', admin.SimpleListFilter),
    ]
    search_fields = ['account', 'owner__username', 'owner__email']
    ordering = ['account']
    readonly_fields = ['created', 'modified', 'mapping_count_display']
    filter_horizontal = ['currencies']
    inlines = [AccountInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('account', 'owner', 'parent', 'enable')
        }),
        ('货币设置', {
            'fields': ('currencies',)
        }),
        ('统计信息', {
            'fields': ('mapping_count_display',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '50'})},
    }
    
    def get_queryset(self, request):
        """优化查询"""
        return super().get_queryset(request).select_related(
            'owner', 'parent'
        ).prefetch_related('currencies', 'children')
    
    def account_type(self, obj):
        """显示账户类型"""
        return obj.get_account_type()
    account_type.short_description = '账户类型'
    account_type.admin_order_field = 'account'
    
    def has_children_display(self, obj):
        """显示是否有子账户"""
        if obj.has_children():
            count = obj.children.count()
            return format_html(
                '<span style="color: green;">是 ({})</span>',
                count
            )
        return format_html('<span style="color: gray;">否</span>')
    has_children_display.short_description = '有子账户'
    
    def mapping_count_display(self, obj):
        """显示映射数量"""
        try:
            from django.apps import apps
            Expense = apps.get_model('maps', 'Expense')
            Assets = apps.get_model('maps', 'Assets')
            Income = apps.get_model('maps', 'Income')
            
            expense_count = Expense.objects.filter(expend=obj, enable=True).count()
            assets_count = Assets.objects.filter(assets=obj, enable=True).count()
            income_count = Income.objects.filter(income=obj, enable=True).count()
            
            total = expense_count + assets_count + income_count
            
            if total > 0:
                return format_html(
                    '<span style="color: blue;">总计: {}<br/>'
                    '支出: {} | 资产: {} | 收入: {}</span>',
                    total, expense_count, assets_count, income_count
                )
            else:
                return format_html('<span style="color: gray;">无映射</span>')
        except:
            return format_html('<span style="color: gray;">无法获取</span>')
    mapping_count_display.short_description = '映射统计'
    
    def currencies_display(self, obj):
        """显示货币"""
        currencies = obj.currencies.all()
        if currencies:
            return ', '.join([c.code for c in currencies])
        return format_html('<span style="color: gray;">无</span>')
    currencies_display.short_description = '货币'
    
    def get_account_type(self, obj):
        """获取账户类型"""
        return obj.get_account_type()
    get_account_type.short_description = '账户类型'
    
    def save_model(self, request, obj, form, change):
        """保存模型时设置属主"""
        if not change:  # 新建时
            obj.owner = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """根据用户权限设置只读字段"""
        readonly_fields = list(self.readonly_fields)
        
        # 非管理员不能修改owner字段
        if not request.user.is_superuser:
            readonly_fields.append('owner')
        
        return readonly_fields
    
    def has_change_permission(self, request, obj=None):
        """检查修改权限"""
        if obj and not request.user.is_superuser:
            return obj.owner == request.user
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """检查删除权限"""
        if obj and not request.user.is_superuser:
            return obj.owner == request.user
        return super().has_delete_permission(request, obj)
    
    class AccountTypeFilter(admin.SimpleListFilter):
        """账户类型过滤器"""
        title = '账户类型'
        parameter_name = 'account_type'
        
        def lookups(self, request, model_admin):
            return [
                ('Assets', '资产账户'),
                ('Liabilities', '负债账户'),
                ('Equity', '权益账户'),
                ('Income', '收入账户'),
                ('Expenses', '支出账户'),
            ]
        
        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(account__startswith=self.value())
            return queryset
    
    # 添加自定义过滤器
    list_filter = [
        'enable', 'owner', 'created', 'modified',
        AccountTypeFilter,
    ]
    
    actions = ['enable_accounts', 'disable_accounts', 'close_accounts']
    
    def enable_accounts(self, request, queryset):
        """批量启用账户"""
        updated = queryset.update(enable=True)
        self.message_user(
            request,
            f'成功启用了 {updated} 个账户。'
        )
    enable_accounts.short_description = "启用选中的账户"
    
    def disable_accounts(self, request, queryset):
        """批量禁用账户"""
        updated = queryset.update(enable=False)
        self.message_user(
            request,
            f'成功禁用了 {updated} 个账户。'
        )
    disable_accounts.short_description = "禁用选中的账户"
    
    def close_accounts(self, request, queryset):
        """批量关闭账户"""
        closed_count = 0
        for account in queryset:
            try:
                account.close()
                closed_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'关闭账户 {account.account} 失败: {str(e)}',
                    level='ERROR'
                )
        
        self.message_user(
            request,
            f'成功关闭了 {closed_count} 个账户。'
        )
    close_accounts.short_description = "关闭选中的账户"
