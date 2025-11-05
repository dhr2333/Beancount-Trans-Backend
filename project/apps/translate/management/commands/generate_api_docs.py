"""
生成API文档的管理命令
"""
import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.settings import spectacular_settings


class Command(BaseCommand):
    help = '生成静态API文档文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='api_docs.json',
            help='输出文件名 (默认: api_docs.json)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'yaml'],
            default='json',
            help='输出格式 (默认: json)'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        output_format = options['format']

        self.stdout.write('正在生成API文档...')

        # 创建schema生成器
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)

        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 根据格式输出文件
        if output_format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
        elif output_format == 'yaml':
            import yaml
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)

        self.stdout.write(
            self.style.SUCCESS(f'API文档已生成: {output_file}')
        )

        # 显示访问URL
        self.stdout.write('\nAPI文档访问地址:')
        self.stdout.write(f'  ReDoc: http://localhost:8000/api/redoc/')
        self.stdout.write(f'  OpenAPI Schema: http://localhost:8000/api/schema/')
