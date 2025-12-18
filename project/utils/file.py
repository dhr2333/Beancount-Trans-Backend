# project/utils/file.py
import io
import os
import re
import tempfile
import PyPDF2
import chardet
import pandas as pd
import hashlib
import logging

from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from project.apps.translate.utils import get_card_number
from project.apps.translate.services.init.strategies.boc_debit_init_strategy import BOCDebitInitStrategy
from project.apps.translate.views.BOC_Debit import boc_debit_pdf_convert_to_string, boc_debit_string_convert_to_csv
from project.apps.translate.services.init.strategies.icbc_debit_init_strategy import ICBCDebitInitStrategy
from project.apps.translate.views.ICBC_Debit import icbc_debit_pdf_convert_to_csv
from project.apps.translate.services.init.strategies.cmb_credit_init_strategy import CMBCreditInitStrategy
from project.apps.translate.views.CMB_Credit import cmb_credit_pdf_convert_to_csv
from project.apps.translate.services.init.strategies.ccb_debit_init_strategy import CCBDebitInitStrategy
from project.apps.translate.views.CCB_Debit import ccb_debit_string_convert_to_csv
from django.conf import settings

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = ['.csv', '.xls', '.xlsx', '.pdf']

def create_temporary_file(file_name):
    """Create a temporary file and return its path."""
    try:
        content = file_name.read()
    except:
        content = file_name
    try:
        encodeing = chardet.detect(content)['encoding']
    except TypeError:
        raise UnsupportedFileTypeError("当前账单不支持")
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(content)
    temp.flush()
    return temp, encodeing

def convert_to_csv_bytes(file, password=None) -> bytes:
    """
    转换为CSV格式以供程序读取解析。

    Args:
        file: 应为 django.core.files.uploadedfile.InMemoryUploadedFile 的实例。
        password (str): PDF文件的密码，如果文件受保护。

    Returns:
        转换后的文件内容（bytes）。
    """
    _, file_extension = os.path.splitext(file.name)
    file_extension = file_extension.lower()

    # 判断文件类型并调用相应的处理函数
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file extension: {file_extension}")

    if file_extension == '.csv':
        return file.read()

    elif file_extension in ['.xls', '.xlsx']:
        return handle_excel(file)

    elif file_extension == '.pdf':
        return handle_pdf(file, password)

def convert_df_to_csv_bytes(df):
    """将DataFrame转换为CSV字节流"""
    csv_content = df.to_csv(index=False, header=False, encoding='utf-8-sig')
    return csv_content.encode('utf-8-sig')

def is_ccb_bill(df):
    """检查是否为建行账单"""
    for _, row in df.iterrows():
        for item in row:
            if pd.notnull(item) and CCBDebitInitStrategy.SOURCE_FILE_IDENTIFIER in str(item):
                return True
    return False

def handle_excel(file):
    df = pd.read_excel(file, header=None, dtype=str)

    df.fillna('', inplace=True)  # 替换NaN为''，避免后续处理中的错误
    if is_ccb_bill(df):
        return ccb_debit_string_convert_to_csv(df)
    elif not df.empty and "微信支付账单明细" in df.iloc[0, 0]:
        return convert_df_to_csv_bytes(df)
    else:
        return convert_df_to_csv_bytes(df)

def handle_pdf(file, password):
    pdf = PyPDF2.PdfReader(file)
    if pdf.is_encrypted:
        if not pdf.decrypt(password):
            raise DecryptionError("PDF解密失败", 401)

    content = extract_text_from_pdf(pdf)

    # 根据内容处理PDF
    if CMBCreditInitStrategy.SOURCE_FILE_IDENTIFIER in content:
        return cmb_credit_pdf_convert_to_csv(content).encode()
    elif BOCDebitInitStrategy.SOURCE_FILE_IDENTIFIER in content:
        card_number = get_card_number(content, BOCDebitInitStrategy.SOURCE_FILE_IDENTIFIER)
        string_content = boc_debit_pdf_convert_to_string(file, password)
        return boc_debit_string_convert_to_csv(string_content, card_number).encode()
    elif ICBCDebitInitStrategy.SOURCE_FILE_IDENTIFIER in content:
        card_number = get_card_number(content, ICBCDebitInitStrategy.SOURCE_FILE_IDENTIFIER)
        return icbc_debit_pdf_convert_to_csv(file, card_number, password).encode()

def extract_text_from_pdf(pdf):
    content = ""
    for page in pdf.pages:
        content += page.extract_text() or ""
    return content

def convert_to_utf8(content_bytes: bytes) -> bytes:
    """将任意编码内容转换为UTF-8字节"""
    try:
        # 检测原始编码
        detected = chardet.detect(content_bytes)
        source_encoding = detected['encoding'] or 'utf-8'

        # 处理中文编码特例
        if source_encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
            source_encoding = 'gb18030'

        # 转换为UTF-8
        try:
            decoded = content_bytes.decode(source_encoding, errors='ignore')
            return decoded.encode('utf-8')
        except (UnicodeDecodeError, LookupError):
            # 回退到常见编码
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    decoded = content_bytes.decode(encoding, errors='ignore')
                    return decoded.encode('utf-8')
                except:
                    continue

            # 最终回退
            return content_bytes.decode('utf-8', errors='ignore').encode('utf-8')

    except Exception as e:
        return content_bytes

def generate_file_hash(file):
    """生成文件哈希值"""
    hasher = hashlib.sha256()
    for chunk in file.chunks():
        hasher.update(chunk)
    file.seek(0)  # 重置文件指针
    return hasher.hexdigest()

def create_text_stream(original_name: str, content: bytes) -> io.StringIO:
    """创建UTF-8编码的文本流对象"""
    # 将字节内容解码为字符串
    content_str = content.decode('utf-8', errors='ignore')

    # 创建内存文本流
    text_stream = io.StringIO(content_str)
    text_stream.name = f"{os.path.splitext(original_name)[0]}_converted.csv"
    return text_stream


class BeanFileManager:
    @staticmethod
    def get_user_assets_path(user_or_username):
        """获取用户资产目录路径
        
        如果用户启用了 Git，使用 repo_name；否则使用 username
        
        Args:
            user_or_username: User 对象或 username 字符串
        
        Returns:
            用户资产目录路径
        """
        # 检查是否为 User 对象
        if hasattr(user_or_username, 'username'):
            user = user_or_username
            # 检查是否有 Git 仓库
            try:
                git_repo = user.git_repo
                return os.path.join(settings.ASSETS_BASE_PATH, git_repo.repo_name)
            except Exception:
                # GitRepository.DoesNotExist 或其他异常，使用 username
                # 这里捕获所有异常，因为 OneToOneField 不存在时会抛出 DoesNotExist
                return os.path.join(settings.ASSETS_BASE_PATH, user.username)
        else:
            # 兼容旧的 username 参数（仅用于非 Git 场景）
            return os.path.join(settings.ASSETS_BASE_PATH, user_or_username)

    @staticmethod
    def ensure_user_assets_dir(user_or_username):
        """确保用户资产目录存在（幂等操作）"""
        user_dir = BeanFileManager.get_user_assets_path(user_or_username)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    @staticmethod
    def ensure_trans_directory(user_or_username):
        """确保trans目录和trans/main.bean文件存在"""
        trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'trans')
        os.makedirs(trans_dir, exist_ok=True)

        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)
        if not os.path.exists(trans_main_path):
            # 创建空的trans/main.bean文件
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.write("; Trans directory - Auto-generated includes\n")
                f.write("; This file is automatically generated by the Beancount-Trans\n\n")
        return trans_dir

    @staticmethod
    def get_bean_file_path(user_or_username, original_filename):
        """获取完整bean文件路径（写入trans/目录）"""
        base_name = os.path.splitext(original_filename)[0]
        trans_dir = os.path.join(
            BeanFileManager.get_user_assets_path(user_or_username),
            'trans'
        )
        os.makedirs(trans_dir, exist_ok=True)
        return os.path.join(trans_dir, f"{base_name}.bean")

    @staticmethod
    def get_main_bean_path(user_or_username):
        """获取用户main.bean文件路径"""
        return os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'main.bean')

    @staticmethod
    def get_trans_main_bean_path(user_or_username):
        """获取trans/main.bean文件路径"""
        trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'trans')
        return os.path.join(trans_dir, 'main.bean')

    @staticmethod
    def create_bean_file(user_or_username, filename):
        """
        创建对应的.bean文件
        :param user_or_username: User 对象或 username 字符串
        :param filename: 原始文件名（不带路径）
        :return: bean文件名（带.bean后缀）
        """
        bean_path = BeanFileManager.get_bean_file_path(user_or_username, filename)
        BeanFileManager.ensure_user_assets_dir(user_or_username)

        if not os.path.exists(bean_path):
            with open(bean_path, 'w', encoding='utf-8') as f:
                pass  # 创建空文件

        return os.path.basename(bean_path)

    @staticmethod
    def update_main_bean_include(user_or_username, bean_filename, action='add'):
        """
        创建适用于 Beancount-Trans 标准的 main.bean 文件
        :param user_or_username: User 对象或 username 字符串
        """
        # 获取用户名（用于模板）
        if hasattr(user_or_username, 'username'):
            username = user_or_username.username
        else:
            username = user_or_username
        
        # 确保 trans/main.bean 文件存在（因为 main.bean 会包含它）
        BeanFileManager.ensure_trans_directory(user_or_username)

        main_bean_path = BeanFileManager.get_main_bean_path(user_or_username)

        # 确保main.bean文件存在
        if not os.path.exists(main_bean_path):
            # 创建目录和文件
            os.makedirs(os.path.dirname(main_bean_path), exist_ok=True)
            with open(main_bean_path, 'w', encoding='utf-8') as f:
                # 使用模板内容，将用户名插入到标题中
                template = f"""; 账本信息
option "title" "{username}的账本"
option "operating_currency" "CNY"

2022-01-01 custom "fava-option" "language" "zh_CN"
2022-01-01 custom "fava-option" "auto-reload" "true"  ; 设置为 true 可使 Fava 在检测到文件更改时自动重新加载页面
2022-01-01 custom "fava-option" "indent" "2"  ; 缩进的数字空格
2022-01-01 custom "fava-option" "sidebar-show-queries" "7"  ; 侧边栏中链接的最大查询数

plugin "beancount.plugins.auto_accounts"  ; 根据条目自动添加账户插件

; 交易记录
include "trans/main.bean"
"""
                f.write(template)
        else:
            # 确保main.bean包含 include "trans/main.bean"
            with open(main_bean_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否包含 include "trans/main.bean"
            trans_main_pattern = re.compile(r'^\s*include\s*"trans/main\.bean"\s*$', re.MULTILINE)
            if not trans_main_pattern.search(content):
                # 如果不存在，添加到文件末尾
                with open(main_bean_path, 'a', encoding='utf-8') as f:
                    if not content.endswith('\n'):
                        f.write('\n')
                    f.write('include "trans/main.bean"\n')

    @staticmethod
    def update_trans_main_bean_include(user_or_username, bean_filename, action='add'):
        """
        更新trans/main.bean文件的include语句（追加方案）
        :param user_or_username: User 对象或 username 字符串
        :param bean_filename: .bean文件名（如 "202505_alipay.bean"）
        :param action: 'add' 或 'remove'
        """
        # 确保trans目录存在
        BeanFileManager.ensure_trans_directory(user_or_username)

        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)

        # 读取现有内容
        with open(trans_main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 构建include语句（相对trans目录）
        include_line = f'include "{bean_filename}"\n'
        include_pattern = re.compile(rf'^\s*include\s*"{re.escape(bean_filename)}"\s*$')

        new_lines = []
        found = False

        # 处理每一行
        for line in lines:
            # 检查是否匹配目标include语句
            if include_pattern.match(line):
                found = True
                if action == 'remove':
                    continue  # 删除该行
            new_lines.append(line)

        # 如果是添加操作且未找到现有行
        if action == 'add' and not found:
            # 在文件末尾添加include语句
            # 确保最后一行有换行符
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append(include_line)

        # 写入更新后的内容
        with open(trans_main_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    @staticmethod
    def delete_bean_file(user_or_username, bean_filename):
        """删除对应的.bean文件（从trans目录）"""
        bean_path = BeanFileManager.get_bean_file_path(user_or_username, bean_filename)
        if os.path.exists(bean_path):
            os.remove(bean_path)

    @staticmethod
    def update_main_bean_username(user_or_username, new_username):
        """更新 main.bean 文件中的用户名引用
        
        Args:
            user_or_username: User 对象或 username 字符串
            new_username: 新用户名
        """
        main_bean_path = BeanFileManager.get_main_bean_path(user_or_username)
        if os.path.exists(main_bean_path):
            with open(main_bean_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新标题中的用户名
            pattern = re.compile(r'option\s+"title"\s+"([^"]+)"')
            def replace_title(match):
                old_title = match.group(1)
                # 如果标题格式为 "{username}的账本"，则更新用户名
                if old_title.endswith('的账本'):
                    return f'option "title" "{new_username}的账本"'
                return match.group(0)
            
            content = pattern.sub(replace_title, content)
            
            with open(main_bean_path, 'w', encoding='utf-8') as f:
                f.write(content)

    @staticmethod
    def rename_user_directory(old_username, new_username):
        """重命名用户目录
        
        Args:
            old_username: 旧用户名
            new_username: 新用户名
        
        Returns:
            bool: 是否成功重命名
        """
        old_path = os.path.join(settings.ASSETS_BASE_PATH, old_username)
        new_path = os.path.join(settings.ASSETS_BASE_PATH, new_username)
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                os.rename(old_path, new_path)
                logger.info(f"Renamed user directory from {old_path} to {new_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to rename user directory: {e}")
                return False
        elif os.path.exists(old_path) and os.path.exists(new_path):
            logger.warning(f"Both old and new directories exist: {old_path} and {new_path}")
            return False
        else:
            logger.warning(f"Old directory does not exist: {old_path}")
            return False
