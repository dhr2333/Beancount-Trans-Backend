# project/apps/account/management/commands/init_official_templates.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from project.apps.account.models import Account, AccountTemplate, AccountTemplateItem
from project.apps.maps.models import Template, TemplateItem
from project.apps.translate.models import FormatConfig

User = get_user_model()

# 从生产环境提取的官方映射数据
# 数据来源: fixtures/20251011-Product.sql
# 提取日期: 2025-10-11
# 支出映射: 519项, 收入映射: 6项, 资产映射: 12项

# 支出映射数据将在方法内定义以避免文件过大


class Command(BaseCommand):
    help = '初始化官方模板和默认用户（id=1）的完整数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-admin',
            action='store_true',
            help='跳过创建admin用户（如果已存在）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建模板（删除现有官方模板）',
        )

    def handle(self, *args, **options):
        skip_admin = options.get('skip_admin', False)
        force = options.get('force', False)

        self.stdout.write(self.style.SUCCESS('开始初始化官方模板和默认用户...'))

        # 1. 检查并创建 id=1 的 admin 用户
        admin_user = self._ensure_admin_user(skip_admin)
        if not admin_user:
            return

        # 2. 创建官方账户模板
        self._create_official_account_template(admin_user, force)

        # 3. 应用官方账户模板到 admin 用户
        self._apply_account_templates_to_admin(admin_user)

        # 4. 创建官方映射模板
        self._create_official_mapping_templates(admin_user, force)

        # 5. 应用官方映射模板到 admin 用户
        self._apply_mapping_templates_to_admin(admin_user)

        # 6. 确保 admin 用户有格式化配置
        self._ensure_format_config(admin_user)

        # 7. 为 admin 用户创建案例文件
        self._create_sample_files_for_admin(admin_user, force)

        self.stdout.write(self.style.SUCCESS('✓ 官方模板和默认用户初始化完成'))

    def _ensure_admin_user(self, skip_admin):
        """确保 id=1 的 admin 用户存在"""
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f'✓ 默认用户已存在: {admin_user.username}'))
            return admin_user
        except User.DoesNotExist:
            if skip_admin:
                self.stdout.write(self.style.WARNING('默认用户（ID=1）不存在，且设置了 --skip-admin'))
                return None

            # 创建 admin 用户
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123456'
            )
            # 确保 ID 为 1
            if admin_user.id != 1:
                self.stdout.write(self.style.WARNING(f'创建的用户 ID={admin_user.id}，不是预期的 ID=1'))

            self.stdout.write(self.style.SUCCESS(f'✓ 创建默认用户: {admin_user.username} (ID={admin_user.id})'))
            return admin_user

    def _create_official_account_template(self, admin_user, force):
        """创建官方账户模板"""
        template_name = "中国用户标准账户模板"

        # 检查模板是否已存在
        existing_template = AccountTemplate.objects.filter(
            name=template_name, 
            is_official=True
        ).first()

        if existing_template:
            if force:
                existing_template.delete()
                self.stdout.write(self.style.WARNING(f'删除现有官方模板: {template_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'官方账户模板已存在: {template_name}，使用 --force 强制重建'))
                return

        # 创建模板
        with transaction.atomic():
            template = AccountTemplate.objects.create(
                name=template_name,
                description="适用于中国用户的标准 Beancount 账户结构",
                is_public=True,
                is_official=True,
                version="1.0.0",
                owner=admin_user
            )

            # 标准账户结构（从生产环境提取）
            # 数据来源: fixtures/20251011-Product.sql
            # 提取日期: 2025-10-11
            # 账户数量: 75个（已包含所有父账户）
            standard_accounts = [
                'Assets',
                'Assets:Receivables',
                'Assets:Receivables:Personal',
                'Assets:Savings',
                'Assets:Savings:Bank',
                'Assets:Savings:Bank:ICBC',
                'Assets:Savings:Bank:ICBC:C5244',
                'Assets:Savings:Recharge',
                'Assets:Savings:Recharge:HaLuo',
                'Assets:Savings:Recharge:LaoPoDaRen',
                'Assets:Savings:Recharge:LiangLiangJiaDao',
                'Assets:Savings:Recharge:LiuXianJi',
                'Assets:Savings:Recharge:Operator',
                'Assets:Savings:Recharge:Operator:Mobile',
                'Assets:Savings:Recharge:Operator:Mobile:C6428',
                'Assets:Savings:Recharge:Operator:Telecom',
                'Assets:Savings:Recharge:Operator:Telecom:C6428',
                'Assets:Savings:Recharge:Operator:Unicom',
                'Assets:Savings:Recharge:Operator:Unicom:C6428',
                'Assets:Savings:Recharge:YiMing',
                'Assets:Savings:Web',
                'Assets:Savings:Web:AliFund',
                'Assets:Savings:Web:AliPay',
                'Assets:Savings:Web:WechatFund',
                'Assets:Savings:Web:WechatPay',
                'Assets:Savings:Web:XiaoHeBao',
                'Equity',
                'Expenses',
                'Expenses:Culture',
                'Expenses:Culture:Education',
                'Expenses:Culture:Entertainment',
                'Expenses:Culture:Subscription',
                'Expenses:Finance',
                'Expenses:Finance:Commission',
                'Expenses:Finance:Insurance',
                'Expenses:Food',
                'Expenses:Food:Breakfast',
                'Expenses:Food:Dinner',
                'Expenses:Food:DrinkFruit',
                'Expenses:Food:Lunch',
                'Expenses:Government',
                'Expenses:Government:Fine',
                'Expenses:Health',
                'Expenses:Health:Medical',
                'Expenses:Health:Outpatient',
                'Expenses:Home',
                'Expenses:Home:Daily',
                'Expenses:Home:Decoration',
                'Expenses:Home:Recharge',
                'Expenses:Shopping',
                'Expenses:Shopping:Clothing',
                'Expenses:Shopping:Digital',
                'Expenses:Shopping:Makeup',
                'Expenses:Shopping:Parent',
                'Expenses:TransPort',
                'Expenses:TransPort:Private',
                'Expenses:TransPort:Private:Fuel',
                'Expenses:TransPort:Private:Park',
                'Expenses:TransPort:Public',
                'Income',
                'Income:Business',
                'Income:LegalSettlements',
                'Income:LegalSettlements:InsuranceClaims',
                'Income:RedPacket',
                'Income:RedPacket:Personal',
                'Income:Sideline',
                'Income:Sideline:DiDi',
                'Liabilities',
                'Liabilities:CreditCard',
                'Liabilities:CreditCard:Bank',
                'Liabilities:CreditCard:Bank:CITIC',
                'Liabilities:CreditCard:Bank:CITIC:C6428',
                'Liabilities:CreditCard:Web',
                'Liabilities:CreditCard:Web:AliPay',
                'Liabilities:CreditCard:Web:DouYin',
            ]

            # 创建模板项
            for account_path in standard_accounts:
                AccountTemplateItem.objects.create(
                    template=template,
                    account_path=account_path,
                    enable=True
                )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方账户模板: {template_name} ({len(standard_accounts)} 个账户)'
            ))

    def _apply_account_templates_to_admin(self, admin_user):
        """应用账户模板到 admin 用户"""
        from project.apps.account.signals import apply_official_account_templates

        # 检查是否已有账户
        existing_count = Account.objects.filter(owner=admin_user).count()
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(
                f'admin 用户已有 {existing_count} 个账户，跳过自动应用'
            ))
            return

        apply_official_account_templates(admin_user)
        final_count = Account.objects.filter(owner=admin_user).count()
        self.stdout.write(self.style.SUCCESS(
            f'✓ 为 admin 用户创建了 {final_count} 个账户'
        ))

    def _ensure_format_config(self, admin_user):
        """确保 admin 用户有格式化配置"""
        config, created = FormatConfig.objects.get_or_create(
            owner=admin_user,
            defaults={
                'flag': '*',
                'show_note': True,
                'show_tag': True,
                'show_time': True,
                'show_uuid': True,
                'show_status': True,
                'show_discount': True,
                'income_template': 'Income:Discount',
                'commission_template': 'Expenses:Finance:Commission',
                'currency': 'CNY',
                'ai_model': 'BERT'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('✓ 创建 admin 用户的格式化配置'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ admin 用户的格式化配置已存在'))

    def _create_official_mapping_templates(self, admin_user, force):
        """创建官方映射模板"""
        from project.apps.account.models import Account

        # 检查现有官方映射模板
        expense_template = Template.objects.filter(name='官方支出映射', is_official=True).first()
        income_template = Template.objects.filter(name='官方收入映射', is_official=True).first()
        assets_template = Template.objects.filter(name='官方资产映射', is_official=True).first()

        # 支出映射模板
        if not expense_template or force:
            if expense_template and force:
                expense_template.delete()

            expense_template = Template.objects.create(
                name='官方支出映射',
                description='中国用户常用支出映射',
                type='expense',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            # 数据来源: fixtures/20251011-Product.sql（生产环境提取）
            # 支出映射项数: 519
            expense_mappings = [
                # 格式: (key, payee, account_path, currency)
                ('乘车', '', 'Expenses:TransPort:Public', ''),
                ('拌饭', '', 'Expenses:Food', ''),
                ('盐选', '知乎', 'Expenses:Culture:Subscription', ''),
                ('透气', '', 'Expenses:Shopping:Clothing', ''),
                ('休闲', '', 'Expenses:Culture', ''),
                ('课外', '', 'Expenses:Culture', ''),
                ('西顿', '西顿照明', 'Expenses:Home:Decoration', ''),
                ('动车', '', 'Expenses:TransPort:Public', ''),
                ('农夫山泉', '农夫山泉', 'Expenses:Food:DrinkFruit', ''),
                ('串串', '', 'Expenses:Food', ''),
                ('茶饮', '', 'Expenses:Food:DrinkFruit', ''),
                ('门票', '', 'Expenses:Culture', ''),
                ('高速', '', 'Expenses:TransPort:Public', ''),
                ('烤肉', '', 'Expenses:Food', ''),
                ('商贸', '', 'Expenses:Shopping', ''),
                ('电子商务', '', 'Expenses:Shopping', ''),
                ('物业费', '', 'Expenses:Home', ''),
                ('医学', '', 'Expenses:Health', ''),
                ('英特尔酷睿', '英特尔', 'Expenses:Shopping:Digital', ''),
                ('音乐', '', 'Expenses:Culture:Entertainment', ''),
                ('月卡', '', 'Expenses:Culture:Subscription', ''),
                ('东方宝石', '东方宝石', 'Expenses:Home:Daily', ''),
                ('保暖', '', 'Expenses:Shopping', ''),
                ('故事', '', 'Expenses:Culture', ''),
                ('炸酱面', '', 'Expenses:Food', ''),
                ('礼品', '', 'Expenses:Culture', ''),
                ('丰巢', '顺丰', 'Expenses:Home', ''),
                ('乐园', '', 'Expenses:Culture', ''),
                ('燃情伴翅', '', 'Expenses:Food', ''),
                ('停泊', '', 'Expenses:TransPort:Private:Park', ''),
                ('服务区', '', 'Expenses:Shopping', ''),
                ('羊肉粉', '', 'Expenses:Food', ''),
                ('当当网', '', 'Expenses:Culture', ''),
                ('家庭装', '', 'Expenses:Home:Daily', ''),
                ('德佑', '德佑', 'Expenses:Home:Daily', ''),
                ('便携', '', 'Expenses:Shopping', ''),
                ('阿斯兰票务', '', 'Expenses:TransPort:Public', ''),
                ('冰粉', '', 'Expenses:Food', ''),
                ('旅客', '', 'Expenses:TransPort:Public', ''),
                ('货拉拉', '货拉拉', 'Expenses:Home', ''),
                ('造型', '', 'Expenses:Shopping:Makeup', ''),
                ('凉皮', '', 'Expenses:Food', ''),
                ('电信', '中国电信', 'Assets:Savings:Recharge:Operator:Telecom:C6428', 'COIN'),
                ('全民K歌', '', 'Expenses:Culture:Entertainment', ''),
                ('美团外卖', '美团', 'Expenses:Food', ''),
                ('泊车', '', 'Expenses:TransPort:Private:Park', ''),
                ('煎饼', '', 'Expenses:Food', ''),
                ('比亚迪', '', 'Expenses:TransPort:Private', ''),
                ('中国移动', '中国移动', 'Assets:Savings:Recharge:Operator:Mobile:C6428', 'COIN'),
                ('云视听', '', 'Expenses:Culture:Entertainment', ''),
                ('南极人', '南极人', 'Expenses:Shopping:Clothing', ''),
                ('韩版', '', 'Expenses:Shopping:Clothing', ''),
                ('家用', '', 'Expenses:Home', ''),
                ('美团', '美团', 'Expenses:Culture', ''),
                ('水杯', '', 'Expenses:Shopping', ''),
                ('凉粉', '', 'Expenses:Food', ''),
                ('店', '', 'Expenses:Shopping', ''),
                ('飞猪', '飞猪', 'Expenses:Home', ''),
                ('通讯', '', 'Expenses:Shopping', ''),
                ('抖音团购', '', 'Expenses:Food', ''),
                ('交通', '', 'Expenses:TransPort:Public', ''),
                ('电器', '', 'Expenses:Shopping:Digital', ''),
                ('物业', '', 'Expenses:Home', ''),
                ('石化', '', 'Expenses:TransPort:Private:Fuel', ''),
                ('浙江移动', '中国移动', 'Assets:Savings:Recharge:Operator:Mobile:C6428', 'COIN'),
                ('沙县小吃', '沙县小吃', 'Expenses:Food', ''),
                ('预调酒', '', 'Expenses:Food:DrinkFruit', ''),
                ('蜜雪冰城', '蜜雪冰城', 'Expenses:Food:DrinkFruit', ''),
                ('停车', '', 'Expenses:TransPort:Private:Park', ''),
                ('浙C', '', 'Expenses:TransPort:Private:Park', ''),
                ('鲜花', '', 'Expenses:Culture', ''),
                ('古茗', '古茗', 'Expenses:Food:DrinkFruit', ''),
                ('益味坊', '益味坊', 'Expenses:Food:Breakfast', ''),
                ('塔斯汀', '塔斯汀', 'Expenses:Food', ''),
                ('十足', '十足', 'Expenses:Food', ''),
                ('一点点', '一点点', 'Expenses:Food:DrinkFruit', ''),
                ('抽纸', '', 'Expenses:Home:Daily', ''),
                ('luckin', '瑞幸', 'Expenses:Food:DrinkFruit', ''),
                ('娘娘大人', '娘娘大人', 'Expenses:Food', ''),
                ('老婆大人', '老婆大人', 'Assets:Savings:Recharge:LaoPoDaRen', 'COIN'),
                ('茶百道', '茶百道', 'Expenses:Food:DrinkFruit', ''),
                ('京东', '京东', 'Expenses:Shopping', ''),
                ('包月', '', 'Expenses:Culture:Subscription', ''),
                ('正新鸡排', '正新鸡排', 'Expenses:Food', ''),
                ('奇虎智能', '360', 'Expenses:Shopping:Digital', ''),
                ('Petal On', '华为', 'Expenses:Culture:Subscription', ''),
                ('药房', '', 'Expenses:Health:Medical', ''),
                ('药店', '', 'Expenses:Health:Medical', ''),
                ('餐饮', '', 'Expenses:Food', ''),
                ('食品', '', 'Expenses:Food', ''),
                ('早餐', '', 'Expenses:Food:Breakfast', ''),
                ('充电', '', 'Expenses:TransPort:Private:Fuel', ''),
                ('加油', '', 'Expenses:TransPort:Private:Fuel', ''),
                ('供电局', '国家电网', 'Expenses:Home:Recharge', ''),
                ('ETC', '', 'Expenses:TransPort:Public', ''),
                ('华为终端有限公司', '华为', 'Expenses:Shopping:Digital', ''),
                ('饿了么', '饿了么', 'Expenses:Food', ''),
                ('美团平台商户', '美团', 'Expenses:Food', ''),
                ('地铁', '', 'Expenses:TransPort:Public', ''),
                ('国网智慧车联网', '国家电网', 'Expenses:TransPort:Private:Fuel', ''),
                ('肯德基', '肯德基', 'Expenses:Food', ''),
                ('华为', '华为', 'Expenses:Shopping', ''),
                ('大疆', '大疆', 'Expenses:Shopping:Digital', ''),
                ('12306', '12306', 'Expenses:TransPort:Public', ''),
                ('阿里云', '阿里云', 'Expenses:Culture:Subscription', ''),
                ('火车票', '', 'Expenses:TransPort:Public', ''),
                ('高铁', '', 'Expenses:TransPort:Public', ''),
                ('机票', '', 'Expenses:TransPort:Public', ''),
                ('医疗', '', 'Expenses:Health:Outpatient', ''),
                ('医生', '', 'Expenses:Health:Outpatient', ''),
                ('医用', '', 'Expenses:Health:Outpatient', ''),
                ('小吃', '', 'Expenses:Food', ''),
                ('餐厅', '', 'Expenses:Food', ''),
                ('小食', '', 'Expenses:Food', ''),
                ('旗舰店', '淘宝', 'Expenses:Shopping', ''),
                ('粮粮驾到', '粮粮驾到', 'Assets:Savings:Recharge:LiangLiangJiaDao', 'COIN'),
                ('中国石油', '中国石油', 'Expenses:TransPort:Private:Fuel', ''),
                ('酒店', '', 'Expenses:Culture', ''),
                ('高德', '高德', 'Expenses:TransPort:Public', ''),
                ('烟酒', '', 'Expenses:Food:DrinkFruit', ''),
                ('理发', '', 'Expenses:Shopping:Makeup', ''),
                ('美发', '', 'Expenses:Shopping:Makeup', ''),
                ('美容', '', 'Expenses:Shopping:Makeup', ''),
                ('果味酒', '', 'Expenses:Food:DrinkFruit', ''),
                ('华莱士', '华莱士', 'Expenses:Food', ''),
                ('晚餐', '', 'Expenses:Food:Dinner', ''),
                ('午餐', '', 'Expenses:Food:Lunch', ''),
                ('鸡尾酒', '', 'Expenses:Food:DrinkFruit', ''),
                ('一鸣', '一鸣', 'Expenses:Food', ''),
                ('之上', '之上', 'Expenses:Food', ''),
                ('水果', '', 'Expenses:Food:DrinkFruit', ''),
                ('会员', '', 'Expenses:Culture:Subscription', ''),
                ('运动', '', 'Expenses:Culture', ''),
                ('纯棉', '', 'Expenses:Shopping', ''),
                ('润肤', '', 'Expenses:Shopping:Makeup', ''),
                ('杯子', '', 'Expenses:Shopping', ''),
                ('小郡肝', '', 'Expenses:Food', ''),
                ('新时沏', '新时沏', 'Expenses:Food:DrinkFruit', ''),
                ('得物', '得物', 'Expenses:Shopping:Clothing', ''),
                ('拼多多', '拼多多', 'Expenses:Shopping', ''),
                ('深圳市腾讯计算机系统有限公司', '腾讯', 'Expenses:Culture', ''),
                ('胖哥俩', '胖哥俩', 'Expenses:Food', ''),
                ('服装', '', 'Expenses:Shopping:Clothing', ''),
                ('衣服', '', 'Expenses:Shopping:Clothing', ''),
                ('裤子', '', 'Expenses:Shopping:Clothing', ''),
                ('鞋子', '', 'Expenses:Shopping:Clothing', ''),
                ('袜子', '', 'Expenses:Shopping:Clothing', ''),
                ('华为软件技术有限公司', '华为', 'Expenses:Culture:Subscription', ''),
                ('淘宝', '淘宝', 'Expenses:Shopping', ''),
                ('医保', '', 'Expenses:Health:Outpatient', ''),
                ('自动续费', '', 'Expenses:Culture:Subscription', ''),
                ('每日坚果', '', 'Expenses:Food', ''),
                ('诊疗', '', 'Expenses:Health:Outpatient', ''),
                ('卫生', '', 'Expenses:Health:Outpatient', ''),
                ('洋酒', '', 'Expenses:Food:DrinkFruit', ''),
                ('彩票', '', 'Expenses:Culture', ''),
                ('超市', '', 'Expenses:Shopping', ''),
                ('大润发', '', 'Expenses:Shopping', ''),
                ('便利店', '', 'Expenses:Shopping', ''),
                ('兰州拉面', '兰州拉面', 'Expenses:Food', ''),
                ('供水', '国家水网', 'Expenses:Home:Recharge', ''),
                ('绝味鸭脖', '绝味鸭脖', 'Expenses:Food', ''),
                ('舒活食品', '一鸣', 'Assets:Savings:Recharge:YiMing', 'COIN'),
                ('抖音生活服务', '抖音', 'Expenses:Food', ''),
                ('医药', '', 'Expenses:Health:Outpatient', ''),
                ('饮料', '', 'Expenses:Food:DrinkFruit', ''),
                ('抖音月付', '抖音', 'Liabilities:CreditCard:Web:DouYin', ''),
                ('公益', '', 'Expenses:Culture', ''),
                ('等多件', '', 'Expenses:Shopping', ''),
                ('喜茶', '喜茶', 'Expenses:Food:DrinkFruit', ''),
                ('倍耐力', '', 'Expenses:TransPort:Private', ''),
                ('娱乐', '', 'Expenses:Culture:Entertainment', ''),
                ('上海拉扎斯信息科技有限公司', '饿了么', 'Expenses:Food', ''),
                ('夜宵', '', 'Expenses:Food:Dinner', ''),
                ('打车', '', 'Expenses:TransPort:Public', ''),
                ('抖音电商', '抖音', 'Expenses:Shopping', ''),
                ('商城', '', 'Expenses:Shopping', ''),
                ('保险', '', 'Expenses:Finance:Insurance', ''),
                ('寄件', '', 'Expenses:Home', ''),
                ('书店', '', 'Expenses:Culture', ''),
                ('外卖', '', 'Expenses:Food', ''),
                ('滴滴出行', '', 'Expenses:TransPort:Public', ''),
                ('公交', '', 'Expenses:TransPort:Public', ''),
                ('航空', '', 'Expenses:TransPort:Public', ''),
                ('储值', '', 'Assets:Savings:Recharge', 'COIN'),
                ('出行', '', 'Expenses:TransPort:Public', ''),
                ('下午茶', '', 'Expenses:Food', ''),
                ('食物', '', 'Expenses:Food', ''),
                ('午饭', '', 'Expenses:Food:Lunch', ''),
                ('晚饭', '', 'Expenses:Food:Dinner', ''),
                ('早饭', '', 'Expenses:Food:Breakfast', ''),
                ('水费', '国家水网', 'Expenses:Home:Recharge', ''),
                ('电费', '国家电网', 'Expenses:Home:Recharge', ''),
                ('物流', '', 'Expenses:Home', ''),
                ('快递', '', 'Expenses:Home', ''),
                ('速递', '', 'Expenses:Home', ''),
                ('App Store', '', 'Expenses:Culture:Subscription', ''),
                ('饭店', '', 'Expenses:Food', ''),
                ('面馆', '', 'Expenses:Food', ''),
                ('服饰', '', 'Expenses:Shopping:Clothing', ''),
                ('METRO', '', 'Expenses:TransPort:Public', ''),
                ('食堂', '', 'Expenses:Food', ''),
                ('生活缴费', '', 'Expenses:Home', ''),
                ('速运', '', 'Expenses:Home', ''),
                ('跑腿', '', 'Expenses:Home', ''),
                ('霸王茶姬', '霸王茶姬', 'Expenses:Food:DrinkFruit', ''),
                ('中医', '', 'Expenses:Health:Outpatient', ''),
                ('理疗', '', 'Expenses:Health:Outpatient', ''),
                ('蛋糕', '蛋糕', 'Expenses:Food', ''),
                ('联通', '中国联通', 'Assets:Savings:Recharge:Operator:Unicom:C6428', 'COIN'),
                ('增值服务', '', 'Expenses:Culture:Subscription', ''),
                ('购物', '', 'Expenses:Shopping', ''),
                ('药业', '', 'Expenses:Health:Medical', ''),
                ('药品', '', 'Expenses:Health:Medical', ''),
                ('牙膏', '', 'Expenses:Home:Daily', ''),
                ('运费', '', 'Expenses:Home', ''),
                ('税务', '', 'Expenses:Government', ''),
                ('充值', '', 'Expenses:Home:Recharge', ''),
                ('订阅', '', 'Expenses:Culture:Subscription', ''),
                ('轮胎', '', 'Expenses:TransPort:Private', ''),
                ('服饰鞋包', '', 'Expenses:Shopping:Clothing', ''),
                ('数码电器', '', 'Expenses:Shopping:Digital', ''),
                ('澜记', '澜记', 'Expenses:Food', ''),
                ('美容美发', '', 'Expenses:Shopping:Makeup', ''),
                ('母婴亲子', '', 'Expenses:Shopping:Parent', ''),
                ('日用百货', '', 'Expenses:Home:Daily', ''),
                ('烧饼', '', 'Expenses:Food', ''),
                ('深圳市腾讯天游科技有限公司', '腾讯', 'Expenses:Culture:Entertainment', ''),
                ('挂号', '', 'Expenses:Health:Outpatient', ''),
                ('体检', '', 'Expenses:Health:Outpatient', ''),
                ('燃气', '瑞安市新奥燃气有限公司', 'Expenses:Home:Recharge', ''),
                ('装修', '', 'Expenses:Home:Decoration', ''),
                ('科沃斯', '科沃斯', 'Expenses:Shopping:Digital', ''),
                ('机器人', '', 'Expenses:Shopping:Digital', ''),
                ('路由器', '', 'Expenses:Shopping:Digital', ''),
                ('批发', '', 'Expenses:Shopping', ''),
                ('小卖部', '', 'Expenses:Shopping', ''),
                ('烧烤', '', 'Expenses:Food', ''),
                ('排档', '', 'Expenses:Food', ''),
                ('洗面奶', '', 'Expenses:Shopping:Makeup', ''),
                ('婴儿', '', 'Expenses:Shopping:Parent', ''),
                ('新生儿', '', 'Expenses:Shopping:Parent', ''),
                ('宝宝', '', 'Expenses:Shopping:Parent', ''),
                ('狂欢价', '', 'Expenses:Shopping', ''),
                ('文具', '', 'Expenses:Culture', ''),
                ('借出', '', 'Assets:Receivables:Personal', ''),
                ('六贤记', '六贤记', 'Assets:Savings:Recharge:LiuXianJi', 'COIN'),
                ('公共交通', '', 'Expenses:TransPort:Public', ''),
                ('美团订单', '美团', 'Expenses:Food', ''),
                ('早教', '', 'Expenses:Shopping:Parent', ''),
                ('玩具', '', 'Expenses:Shopping:Parent', ''),
                ('新生', '', 'Expenses:Shopping:Parent', ''),
                ('益智', '', 'Expenses:Shopping:Parent', ''),
                ('贝亲', '贝亲', 'Expenses:Shopping:Parent', ''),
                ('便利', '', 'Expenses:Shopping', ''),
                ('可口可乐', '江苏太古可口可乐饮料有限公司', 'Expenses:Food:DrinkFruit', ''),
                ('爱奇艺', '爱奇艺', 'Expenses:Culture:Subscription', ''),
                ('大衣', '', 'Expenses:Shopping:Clothing', ''),
                ('汉堡', '', 'Expenses:Food', ''),
                ('光明', '光明', 'Expenses:Food:DrinkFruit', ''),
                ('轨道交通', '', 'Expenses:TransPort:Public', ''),
                ('酸奶', '', 'Expenses:Food:DrinkFruit', ''),
                ('淮南牛肉汤', '', 'Expenses:Food', ''),
                ('短裤', '', 'Expenses:Shopping:Clothing', ''),
                ('温州店', '', 'Expenses:Shopping', ''),
                ('肠粉', '', 'Expenses:Food', ''),
                ('大众点评', '', 'Expenses:Food', ''),
                ('秋季', '', 'Expenses:Shopping:Clothing', ''),
                ('锅贴', '', 'Expenses:Food', ''),
                ('顺丰', '顺丰', 'Expenses:Home', ''),
                ('百货', '', 'Expenses:Shopping', ''),
                ('护肤品', '', 'Expenses:Shopping:Makeup', ''),
                ('转接头', '', 'Expenses:Shopping:Digital', ''),
                ('新奥', '瑞安市新奥燃气有限公司', 'Expenses:Home:Recharge', ''),
                ('早餐奶', '', 'Expenses:Food:DrinkFruit', ''),
                ('雨伞', '', 'Expenses:Shopping', ''),
                ('冒菜', '', 'Expenses:Food', ''),
                ('影院', '', 'Expenses:Culture:Entertainment', ''),
                ('披萨', '', 'Expenses:Food', ''),
                ('鲜奶', '', 'Expenses:Food:DrinkFruit', ''),
                ('果茶', '', 'Expenses:Food:DrinkFruit', ''),
                ('安慕希', '安慕希', 'Expenses:Food:DrinkFruit', ''),
                ('炸串', '', 'Expenses:Food', ''),
                ('中裤', '', 'Expenses:Shopping:Clothing', ''),
                ('瑞安店', '', 'Expenses:Shopping', ''),
                ('杂粮煎饼', '', 'Expenses:Food', ''),
                ('酸辣粉', '', 'Expenses:Food', ''),
                ('海飞丝', '宝洁', 'Expenses:Home:Daily', ''),
                ('三只松鼠', '三只松鼠', 'Expenses:Food', ''),
                ('1点点', '一点点', 'Expenses:Food:DrinkFruit', ''),
                ('McDonalds', '麦当劳', 'Expenses:Food', ''),
                ('护肤水', '', 'Expenses:Shopping:Makeup', ''),
                ('化妆品', '', 'Expenses:Shopping:Makeup', ''),
                ('男鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('淘票票', '淘票票', 'Expenses:Culture:Entertainment', ''),
                ('零食', '', 'Expenses:Food', ''),
                ('太阳伞', '', 'Expenses:Shopping', ''),
                ('影城', '', 'Expenses:Culture:Entertainment', ''),
                ('纯牛奶', '', 'Expenses:Food:DrinkFruit', ''),
                ('公路运输', '', 'Expenses:TransPort:Public', ''),
                ('运动裤', '', 'Expenses:Shopping:Clothing', ''),
                ('酒吧', '', 'Expenses:Culture:Education', ''),
                ('点心', '', 'Expenses:Food', ''),
                ('杰士邦', '杰士邦', 'Expenses:Home:Daily', ''),
                ('美团点评', '美团', 'Expenses:Food', ''),
                ('米粉', '', 'Expenses:Food', ''),
                ('麦当劳', '麦当劳', 'Expenses:Food', ''),
                ('睡衣', '', 'Expenses:Shopping:Clothing', ''),
                ('洁面', '', 'Expenses:Shopping:Makeup', ''),
                ('运动鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('希望树', '希望树', 'Expenses:Home:Daily', ''),
                ('网络服务', '', 'Expenses:Culture:Subscription', ''),
                ('插板', '', 'Expenses:Home:Decoration', ''),
                ('点餐', '', 'Expenses:Food', ''),
                ('统一公共支付平台', '', 'Expenses:Government:Fine', ''),
                ('口红', '', 'Expenses:Shopping:Makeup', ''),
                ('医院', '', 'Expenses:Health:Outpatient', ''),
                ('门诊', '', 'Expenses:Health:Outpatient', ''),
                ('小杨生煎', '小杨生煎', 'Expenses:Food', ''),
                ('借款', '', 'Assets:Receivables:Personal', ''),
                ('宾馆', '', 'Expenses:Culture', ''),
                ('UNIQLO', '优衣库', 'Expenses:Shopping:Clothing', ''),
                ('口腔', '', 'Expenses:Health', ''),
                ('早点', '', 'Expenses:Food:Breakfast', ''),
                ('网咖', '', 'Expenses:Culture:Entertainment', ''),
                ('凡士林', '凡士林', 'Expenses:Shopping:Makeup', ''),
                ('财产保险', '', 'Expenses:Finance:Insurance', ''),
                ('商品', '', 'Expenses:Shopping', ''),
                ('虎邦辣酱', '虎邦辣酱', 'Expenses:Food', ''),
                ('教育', '', 'Expenses:Culture:Education', ''),
                ('煲仔', '', 'Expenses:Food', ''),
                ('拉扎斯网络科技', '饿了么', 'Expenses:Food', ''),
                ('粉干', '', 'Expenses:Food', ''),
                ('电动牙刷', '', 'Expenses:Shopping:Digital', ''),
                ('化妆水', '', 'Expenses:Shopping:Makeup', ''),
                ('电动', '', 'Expenses:Shopping:Digital', ''),
                ('老爹鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('无印良品', '无印良品', 'Expenses:Home', ''),
                ('沐浴乳', '', 'Expenses:Home:Daily', ''),
                ('旅馆', '', 'Expenses:Culture', ''),
                ('优衣库', '优衣库', 'Expenses:Shopping:Clothing', ''),
                ('串串香', '', 'Expenses:Food', ''),
                ('打印', '', 'Expenses:Culture:Education', ''),
                ('网吧', '', 'Expenses:Culture:Entertainment', ''),
                ('卤肉饭', '', 'Expenses:Food', ''),
                ('芯片', '', 'Expenses:Shopping:Digital', ''),
                ('分裤', '', 'Expenses:Shopping:Clothing', ''),
                ('眼镜', '', 'Expenses:Home:Daily', ''),
                ('遮阳伞', '', 'Expenses:Home:Daily', ''),
                ('冬季', '', 'Expenses:Shopping:Clothing', ''),
                ('葱油饼', '', 'Expenses:Food', ''),
                ('汉庭', '', 'Expenses:Culture', ''),
                ('KFC', '肯德基', 'Expenses:Food', ''),
                ('刷头', '', 'Expenses:Home:Daily', ''),
                ('精华水', '', 'Expenses:Shopping:Makeup', ''),
                ('内裤', '', 'Expenses:Shopping:Clothing', ''),
                ('Muji', '无印良品', 'Expenses:Home', ''),
                ('周黑鸭', '周黑鸭', 'Expenses:Food', ''),
                ('鲜芋仙', '鲜芋仙', 'Expenses:Food:DrinkFruit', ''),
                ('海底捞', '海底捞', 'Expenses:Food', ''),
                ('火锅', '', 'Expenses:Food', ''),
                ('蒙牛', '蒙牛', 'Expenses:Food:DrinkFruit', ''),
                ('麻辣烫', '', 'Expenses:Food', ''),
                ('奈雪の茶', '奈雪の茶', 'Expenses:Food:DrinkFruit', ''),
                ('快餐', '', 'Expenses:Food', ''),
                ('阿里健康大药房', '阿里健康大药房', 'Expenses:Health', ''),
                ('漱口水', '', 'Expenses:Home:Daily', ''),
                ('酸菜鱼', '', 'Expenses:Food', ''),
                ('春季', '', 'Expenses:Shopping:Clothing', ''),
                ('谷田稻香', '谷田稻香', 'Expenses:Food', ''),
                ('华住', '', 'Expenses:Culture', ''),
                ('馄饨', '', 'Expenses:Food', ''),
                ('爽肤水', '', 'Expenses:Shopping:Makeup', ''),
                ('蓝牙', '', 'Expenses:Shopping:Digital', ''),
                ('烘焙', '', 'Expenses:Food', ''),
                ('半身裙', '', 'Expenses:Shopping:Clothing', ''),
                ('牛仔', '', 'Expenses:Shopping:Clothing', ''),
                ('短裙', '', 'Expenses:Shopping:Clothing', ''),
                ('裙子', '', 'Expenses:Shopping:Clothing', ''),
                ('速冻', '', 'Expenses:Food', ''),
                ('菜鸟', '', 'Expenses:Home', ''),
                ('美甲', '', 'Expenses:Shopping:Makeup', ''),
                ('穿戴甲', '', 'Expenses:Shopping:Makeup', ''),
                ('纸尿裤', '', 'Expenses:Shopping:Parent', ''),
                ('拉拉裤', '', 'Expenses:Shopping:Parent', ''),
                ('长袖', '', 'Expenses:Shopping:Clothing', ''),
                ('短袖', '', 'Expenses:Shopping:Clothing', ''),
                ('夹克', '', 'Expenses:Shopping:Clothing', ''),
                ('面膜', '', 'Expenses:Shopping:Makeup', ''),
                ('连衣裙', '', 'Expenses:Shopping:Clothing', ''),
                ('背带裙', '', 'Expenses:Shopping:Clothing', ''),
                ('吊带', '', 'Expenses:Shopping:Clothing', ''),
                ('背心', '', 'Expenses:Shopping:Clothing', ''),
                ('遮瑕', '', 'Expenses:Shopping:Makeup', ''),
                ('隔离霜', '', 'Expenses:Shopping:Makeup', ''),
                ('高跟鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('光腿神器', '', 'Expenses:Shopping:Clothing', ''),
                ('打底裤', '', 'Expenses:Shopping:Clothing', ''),
                ('丝袜', '', 'Expenses:Shopping:Clothing', ''),
                ('卫生巾', '', 'Expenses:Home:Daily', ''),
                ('内衣', '', 'Expenses:Shopping:Clothing', ''),
                ('雪地靴', '', 'Expenses:Shopping:Clothing', ''),
                ('棉鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('精华液', '', 'Expenses:Shopping:Makeup', ''),
                ('笔记本电脑', '', 'Expenses:Shopping:Digital', ''),
                ('**', '', 'Expenses:Shopping', ''),
                ('重庆小面', '', 'Expenses:Food', ''),
                ('湿巾', '', 'Expenses:Home:Daily', ''),
                ('纸巾', '', 'Expenses:Home:Daily', ''),
                ('十月结晶', '十月结晶', 'Expenses:Shopping:Parent', ''),
                ('文胸', '', 'Expenses:Shopping:Clothing', ''),
                ('隆江猪脚饭', '', 'Expenses:Food', ''),
                ('电影票', '', 'Expenses:Culture:Entertainment', ''),
                ('杜蕾斯', '杜蕾斯', 'Expenses:Home:Daily', ''),
                ('安全套', '', 'Expenses:Home:Daily', ''),
                ('避孕套', '', 'Expenses:Home:Daily', ''),
                ('游戏', '', 'Expenses:Culture:Entertainment', ''),
                ('周边', '', 'Expenses:Culture:Entertainment', ''),
                ('衬衫', '', 'Expenses:Shopping:Clothing', ''),
                ('衬衣', '', 'Expenses:Shopping:Clothing', ''),
                ('永和豆浆', '永和豆浆', 'Expenses:Food', ''),
                ('书籍', '', 'Expenses:Culture:Education', ''),
                ('读物', '', 'Expenses:Culture:Education', ''),
                ('简餐', '', 'Expenses:Food', ''),
                ('上衣', '', 'Expenses:Shopping:Clothing', ''),
                ('便当', '', 'Expenses:Food', ''),
                ('沐浴露', '', 'Expenses:Home:Daily', ''),
                ('洗发水', '', 'Expenses:Home:Daily', ''),
                ('护发素', '', 'Expenses:Home:Daily', ''),
                ('修身', '', 'Expenses:Shopping:Clothing', ''),
                ('春装', '', 'Expenses:Shopping:Clothing', ''),
                ('夏装', '', 'Expenses:Shopping:Clothing', ''),
                ('秋装', '', 'Expenses:Shopping:Clothing', ''),
                ('冬装', '', 'Expenses:Shopping:Clothing', ''),
                ('滴滴', '', 'Expenses:TransPort:Public', ''),
                ('奶茶', '', 'Expenses:Food:DrinkFruit', ''),
                ('短袜', '', 'Expenses:Shopping:Clothing', ''),
                ('长袜', '', 'Expenses:Shopping:Clothing', ''),
                ('中筒袜', '', 'Expenses:Shopping:Clothing', ''),
                ('帆布鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('防晒霜', '', 'Expenses:Shopping:Makeup', ''),
                ('黄焖鸡', '', 'Expenses:Food', ''),
                ('金华烧饼', '', 'Expenses:Food', ''),
                ('永嘉麦饼', '', 'Expenses:Food', ''),
                ('船袜', '', 'Expenses:Shopping:Clothing', ''),
                ('板鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('休闲鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('休闲裤', '', 'Expenses:Shopping:Clothing', ''),
                ('吹风机', '', 'Expenses:Shopping:Digital', ''),
                ('眼影盘', '', 'Expenses:Shopping:Makeup', ''),
                ('防晒服', '', 'Expenses:Shopping:Clothing', ''),
                ('瑜珈垫', '', 'Expenses:Home', ''),
                ('滴眼液', '', 'Expenses:Health', ''),
                ('眼药水', '', 'Expenses:Health', ''),
                ('拖鞋', '', 'Expenses:Shopping:Clothing', ''),
                ('充电器', '', 'Expenses:Shopping:Digital', ''),
                ('U盘', '', 'Expenses:Shopping:Digital', ''),
                ('金士顿', '金士顿', 'Expenses:Shopping:Digital', ''),
                ('盖浇饭', '', 'Expenses:Food', ''),
                ('香水', '', 'Expenses:Shopping:Makeup', ''),
                ('外套', '', 'Expenses:Shopping:Clothing', ''),
                ('情趣用品', '', 'Expenses:Home:Daily', ''),
                ('洗衣液', '', 'Expenses:Home:Daily', ''),
                ('高领', '', 'Expenses:Shopping:Clothing', ''),
                ('毛衣', '', 'Expenses:Shopping:Clothing', ''),
                ('棉衣', '', 'Expenses:Shopping:Clothing', ''),
                ('棉袄', '', 'Expenses:Shopping:Clothing', ''),
                ('棉服', '', 'Expenses:Shopping:Clothing', ''),
                ('针织衫', '', 'Expenses:Shopping:Clothing', ''),
                ('面霜', '', 'Expenses:Shopping:Makeup', ''),
                ('护手霜', '', 'Expenses:Shopping:Makeup', ''),
                ('唇釉', '', 'Expenses:Shopping:Makeup', ''),
                ('唇膏', '', 'Expenses:Shopping:Makeup', ''),
                ('RIO', 'RIO', 'Expenses:Food:DrinkFruit', ''),
                ('锐澳', 'RIO', 'Expenses:Food:DrinkFruit', ''),
                ('美食', '', 'Expenses:Food', ''),
                ('N多寿司', 'N多寿司', 'Expenses:Food', ''),
                ('千层', '千层', 'Expenses:Food', ''),
                ('炸鸡', '', 'Expenses:Food', ''),
                ('伊利', '伊利', 'Expenses:Food:DrinkFruit', ''),
                ('CoCo', 'CoCo', 'Expenses:Food:DrinkFruit', ''),
                ('台球', '', 'Expenses:Culture:Entertainment', ''),
                ('鸭血粉丝汤', '', 'Expenses:Food', ''),
                ('阔腿裤', '', 'Expenses:Shopping:Clothing', ''),
                ('果品', '', 'Expenses:Food:DrinkFruit', ''),
                ('百岁我家', '百岁我家', 'Expenses:Food', ''),
                ('夏季', '', 'Expenses:Shopping:Clothing', ''),
                ('网易游戏', '网易', 'Expenses:Culture:Entertainment', ''),
                ('生煎', '', 'Expenses:Food', ''),
                ('鸭血粉丝', '', 'Expenses:Food', ''),
                ('续费', '', 'Expenses:Culture:Subscription', ''),
                ('88VIP', '', 'Expenses:Culture:Subscription', ''),
                ('转换器', '', 'Expenses:Shopping:Digital', ''),
                ('运费险', '', 'Expenses:Finance:Insurance', ''),
                ('软件', '', 'Expenses:Culture', ''),
                ('吸汗', '', 'Expenses:Shopping:Clothing', ''),
                ('回力', '回力', 'Expenses:Shopping', ''),
                ('阅读', '', 'Expenses:Culture', ''),
                ('商户', '', 'Expenses:Shopping', ''),
                ('消费', '', 'Expenses:Shopping', ''),
                ('中饭', '', 'Expenses:Food:Lunch', ''),
                ('宽带', '', 'Expenses:Culture:Subscription', ''),
                ('民宿', '', 'Expenses:Culture', ''),
                ('特来电', '', 'Expenses:TransPort:Private:Fuel', ''),
                ('宜宾燃面', '', 'Expenses:Food', ''),
                ('途虎', '', 'Expenses:TransPort:Private', ''),
                ('吃饭', '', 'Expenses:Food', ''),
                ('收钱服务费', '', 'Expenses:Finance:Commission', ''),
                ('电玩', '', 'Expenses:Culture:Entertainment', ''),
                ('衢州鸭头', '', 'Expenses:Food', ''),
                ('米线', '', 'Expenses:Food', ''),
                ('自如', '', 'Expenses:Culture', ''),
                ('茶叶', '', 'Expenses:Culture', ''),
                ('口罩', '', 'Expenses:Health:Outpatient', ''),
                ('双肩包', '', 'Expenses:Shopping:Clothing', ''),
                ('背包', '', 'Expenses:Shopping:Clothing', ''),
                ('斜挎包', '', 'Expenses:Shopping:Clothing', ''),
                ('单肩包', '', 'Expenses:Shopping:Clothing', ''),
                ('耳机', '', 'Expenses:Shopping:Digital', ''),
            ]

            for key, payee, account_path, currency in expense_mappings:
                TemplateItem.objects.create(
                    template=expense_template,
                    key=key,
                    payee=payee if payee else None,
                    account=account_path,  # 直接使用账户路径字符串
                    currency=currency
                )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方支出映射模板 ({len(expense_mappings)} 项)'
            ))

        # 资产映射模板
        if not assets_template or force:
            if assets_template and force:
                assets_template.delete()

            assets_template = Template.objects.create(
                name='官方资产映射',
                description='中国用户常用资产映射',
                type='assets',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            # 资产映射 (key, full, account_path)
            assets_mappings = [
                ('零钱通', '微信零钱通', 'Assets:Savings:Web:WechatFund'),
                ('零钱', '微信零钱', 'Assets:Savings:Web:WechatPay'),
                ('余额宝', '支付宝余额宝', 'Assets:Savings:Web:AliFund'),
                ('余额', '支付宝余额', 'Assets:Savings:Web:AliPay'),
                ('账户余额', '支付宝余额', 'Assets:Savings:Web:AliPay'),
                ('花呗', '支付宝花呗', 'Liabilities:CreditCard:Web:AliPay'),
                ('/', '微信零钱', 'Assets:Savings:Web:WechatPay'),
                ('单车骑行卡抵扣', '单车骑行卡抵扣', 'Assets:Savings:Recharge:HaLuo'),
                ('借呗', '支付宝借呗', 'Liabilities:CreditCard:Web:AliPay'),
                ('备用金', '支付宝备用金', 'Liabilities:CreditCard:Web:AliPay'),
                ('6428', '中信银行信用卡(6428)', 'Liabilities:CreditCard:Bank:CITIC:C6428'),
                ('5244', '中国工商银行储蓄卡(5244)', 'Assets:Savings:Bank:ICBC:C5244'),
]

            for key, full, account_path in assets_mappings:
                TemplateItem.objects.create(
                    template=assets_template,
                    key=key,
                    full=full,
                    account=account_path  # 直接使用账户路径字符串
                )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方资产映射模板 ({len(assets_mappings)} 项)'
            ))

        # 收入映射模板
        if not income_template or force:
            if income_template and force:
                income_template.delete()

            income_template = Template.objects.create(
                name='官方收入映射',
                description='中国用户常用收入映射',
                type='income',
                is_public=True,
                is_official=True,
                version='1.0.0',
                owner=admin_user
            )

            # 收入映射 (key, payer, account_path)
            income_mappings = [
                # 格式: (key, payer, account_path)
                ('小荷包', None, 'Assets:Savings:Web:XiaoHeBao'),
                ('收钱码经营版收款', None, 'Income:Business'),
                ('出行账户余额提现', None, 'Income:Sideline:DiDi'),
                ('理赔', None, 'Income:LegalSettlements:InsuranceClaims'),
                ('红包', None, 'Income:RedPacket:Personal'),
                ('老婆', None, 'Assets:Receivables:Personal'),
]

            for key, payer, account_path in income_mappings:
                TemplateItem.objects.create(
                    template=income_template,
                    key=key,
                    payer=payer,
                    account=account_path  # 直接使用账户路径字符串
                )

            self.stdout.write(self.style.SUCCESS(
                f'✓ 创建官方收入映射模板 ({len(income_mappings)} 项)'
            ))

    def _apply_mapping_templates_to_admin(self, admin_user):
        """应用映射模板到 admin 用户"""
        from project.apps.maps.signals import apply_official_templates
        from project.apps.maps.models import Expense, Assets, Income

        # 检查是否已有映射
        existing_expenses = Expense.objects.filter(owner=admin_user).count()
        existing_assets = Assets.objects.filter(owner=admin_user).count()
        existing_incomes = Income.objects.filter(owner=admin_user).count()
        total_existing = existing_expenses + existing_assets + existing_incomes

        if total_existing > 0:
            self.stdout.write(self.style.WARNING(
                f'admin 用户已有 {total_existing} 个映射，跳过自动应用'
            ))
            return

        apply_official_templates(admin_user)

        final_expenses = Expense.objects.filter(owner=admin_user).count()
        final_assets = Assets.objects.filter(owner=admin_user).count()
        final_incomes = Income.objects.filter(owner=admin_user).count()

        self.stdout.write(self.style.SUCCESS(
            f'✓ 为 admin 用户创建映射: 支出={final_expenses}, 资产={final_assets}, 收入={final_incomes}'
        ))

    def _create_sample_files_for_admin(self, admin_user, force):
        """为 admin 用户创建案例文件"""
        from project.apps.file_manager.models import Directory, File
        from project.apps.translate.models import ParseFile
        from project.utils.storage_factory import get_storage_client
        from project.utils.file import generate_file_hash, BeanFileManager
        import os

        # 获取或创建 Root 目录
        root_dir = Directory.objects.filter(
            name='Root',
            owner=admin_user,
            parent__isnull=True
        ).first()

        if not root_dir:
            root_dir = Directory.objects.create(
                name='Root',
                owner=admin_user,
                parent=None
            )

        # 检查是否已有案例文件
        existing_files = File.objects.filter(
            owner=admin_user,
            directory=root_dir,
            name__in=['完整测试_微信.csv', '完整测试_支付宝.csv']
        )

        if existing_files.exists():
            if force:
                existing_files.delete()
                self.stdout.write(self.style.WARNING('删除现有案例文件'))
            else:
                self.stdout.write(self.style.WARNING('案例文件已存在，使用 --force 强制重建'))
                return

        # 案例文件配置
        sample_files = [
            {
                'name': '完整测试_微信.csv',
                'directory': root_dir,
                'local_path': 'fixtures/sample_files/完整测试_微信.csv',
                'content_type': 'text/csv'
            },
            {
                'name': '完整测试_支付宝.csv',
                'directory': root_dir,
                'local_path': 'fixtures/sample_files/完整测试_支付宝.csv',
                'content_type': 'text/csv'
            }
        ]

        storage_client = get_storage_client()
        created_files = []

        for file_config in sample_files:
            local_path = file_config['local_path']

            # 检查本地文件是否存在
            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(f'本地文件不存在: {local_path}，跳过'))
                continue

            # 读取文件内容
            with open(local_path, 'rb') as f:
                file_content = f.read()

            # 生成文件哈希和存储名称
            import hashlib
            hasher = hashlib.sha256()
            hasher.update(file_content)
            file_hash = hasher.hexdigest()
            file_extension = os.path.splitext(file_config['name'])[1]
            storage_name = f"{file_hash}{file_extension}"

            # 上传到存储
            from io import BytesIO
            file_stream = BytesIO(file_content)

            success = storage_client.upload_file(
                storage_name,
                file_stream,
                content_type=file_config['content_type']
            )

            if not success:
                self.stdout.write(self.style.ERROR(f'文件上传失败: {file_config["name"]}'))
                continue

            # 创建文件记录
            file_obj = File.objects.create(
                name=file_config['name'],
                directory=file_config['directory'],
                storage_name=storage_name,
                size=len(file_content),
                owner=admin_user,
                content_type=file_config['content_type']
            )

            # 创建解析记录
            ParseFile.objects.create(file=file_obj)

            # 创建对应的 .bean 文件
            bean_filename = BeanFileManager.create_bean_file(
                admin_user.username,
                file_config['name']
            )
            # 上传文件时即向trans/main.bean增加对应文件的include
            BeanFileManager.add_bean_to_trans_main(
                admin_user.username,
                bean_filename
            )

            created_files.append(file_config['name'])

        self.stdout.write(self.style.SUCCESS(
            f'✓ 为 admin 用户创建案例文件: {len(created_files)} 个文件'
        ))
        for filename in created_files:
            self.stdout.write(f'  - {filename}')

