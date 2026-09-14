# project/utils/file.py
import io
import os
import re
import shutil
import tempfile
import zipfile
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


SUPPORTED_EXTENSIONS = ['.csv', '.xls', '.xlsx', '.pdf', '.zip']

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
        password (str): PDF/ZIP 文件的解密密码，若文件受保护。

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

    elif file_extension == '.zip':
        return handle_zip(file, password)

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
        if password is None or (isinstance(password, str) and not password.strip()):
            raise DecryptionError("PDF 文件已加密，请提供解密密码", 401)
        if not pdf.decrypt(password):
            raise DecryptionError("PDF 解密失败：口令错误或文件已损坏", 401)

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
    else:
        raise UnsupportedFileTypeError("该 PDF 不是支持的账单类型（仅支持招商信用卡、中行/工行储蓄卡账单）")

def handle_zip(file, password=None):
    """
    解压 ZIP 文件并提取第一个支持的账单文件（csv/xls/xlsx/pdf），再转换为 CSV 字节。

    Args:
        file: 上传的 ZIP 文件对象
        password (str): ZIP 解压密码，若压缩包受保护

    Returns:
        转换后的文件内容（bytes）
    """
    file.seek(0)
    raw = file.read()
    pwd = password.encode('utf-8') if password else None

    try:
        with zipfile.ZipFile(io.BytesIO(raw), 'r') as zf:
            # 查找第一个支持的扩展名
            supported = {ext.lower() for ext in SUPPORTED_EXTENSIONS if ext != '.zip'}
            target_info = None
            for info in zf.infolist():
                if info.is_dir():
                    continue
                _, ext = os.path.splitext(info.filename)
                if ext.lower() in supported:
                    target_info = info
                    break

            if not target_info:
                raise UnsupportedFileTypeError("ZIP 压缩包内未找到支持的账单文件（csv/xls/xlsx/pdf）")

            try:
                inner_bytes = zf.read(target_info, pwd=pwd)
            except RuntimeError as e:
                if 'password' in str(e).lower() or 'bad password' in str(e).lower():
                    raise DecryptionError("ZIP 解密失败：口令错误或文件已损坏", 401)
                raise
            except zipfile.BadZipFile:
                raise DecryptionError("ZIP 解密失败：口令错误或文件已损坏", 401)

            # 构造类文件对象供 convert_to_csv_bytes 使用
            inner_name = os.path.basename(target_info.filename)
            inner_file = io.BytesIO(inner_bytes)
            inner_file.name = inner_name

            return convert_to_csv_bytes(inner_file, password)
    except zipfile.BadZipFile as e:
        logger.warning("ZIP 文件损坏或格式错误")
        raise UnsupportedFileTypeError("ZIP 文件损坏或格式不正确")
    except DecryptionError:
        raise
    except UnsupportedFileTypeError:
        raise


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

    # @staticmethod
    # def ensure_trans_directory(user_or_username):
    #     """确保trans目录和trans/main.bean文件存在"""
    #     trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'trans')
    #     os.makedirs(trans_dir, exist_ok=True)

    #     trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)
    #     if not os.path.exists(trans_main_path):
    #         # 创建空的trans/main.bean文件
    #         with open(trans_main_path, 'w', encoding='utf-8') as f:
    #             f.write("; Trans directory - Auto-generated includes\n")
    #             f.write("; This file is automatically generated by the Beancount-Trans\n\n")
    #     return trans_dir

    @staticmethod
    def _normalize_relative_path(relative_path):
        """规范化 trans/ 下的相对路径（统一为 POSIX 分隔符）

        过滤空段、"." 与 ".." 段，等价于剥离开头的路径分隔符，
        从而保证结果始终位于 trans/ 目录之下。

        Args:
            relative_path: 以 "/" 或当前系统分隔符表示的相对路径

        Returns:
            str: 以 "/" 分隔的规范化相对路径，空路径返回 ""
        """
        if not relative_path:
            return ""
        segments = re.split(r'[/\\]+', str(relative_path))
        parts = [s.strip() for s in segments if s.strip() and s.strip() not in ('.', '..')]
        return "/".join(parts)

    @staticmethod
    def _resolve_trans_path(user_or_username, relative_bean_path):
        """将 trans/ 下的相对路径解析为绝对路径（防御目录穿越）

        Args:
            user_or_username: User 对象或 username 字符串
            relative_bean_path: 相对于 trans/ 的路径（POSIX 或系统分隔符）

        Returns:
            str: trans/ 下的绝对路径，relative_bean_path 为空时返回 trans/ 目录本身
        """
        trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'trans')
        normalized = BeanFileManager._normalize_relative_path(relative_bean_path)
        if not normalized:
            return trans_dir
        return os.path.join(trans_dir, normalized.replace('/', os.sep))

    @staticmethod
    def _cleanup_empty_dirs(user_or_username, start_dir):
        """删除 trans/ 目录下的空父目录（不会删除 trans/ 本身）

        Args:
            user_or_username: User 对象或 username 字符串
            start_dir: 从该目录开始向上清理
        """
        trans_dir = os.path.abspath(os.path.join(
            BeanFileManager.get_user_assets_path(user_or_username), 'trans'))
        current = os.path.abspath(start_dir)
        while current != trans_dir and current.startswith(trans_dir + os.sep):
            try:
                if not os.path.isdir(current) or os.listdir(current):
                    break
                os.rmdir(current)
            except OSError:
                break
            current = os.path.dirname(current)

    @staticmethod
    def get_bean_file_path(user_or_username, original_filename, relative_dir=""):
        """获取完整bean文件路径（写入trans/目录，支持子目录）

        Args:
            user_or_username: User 对象或 username 字符串
            original_filename: 原始文件名（不带路径）
            relative_dir: 相对于 trans/ 的子目录（POSIX 或系统分隔符），默认为空

        Returns:
            str: trans/ 下（含子目录）的完整bean文件路径
        """
        base_name = os.path.splitext(original_filename)[0]
        trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username),'trans')
        normalized_dir = BeanFileManager._normalize_relative_path(relative_dir)
        target_dir = os.path.join(trans_dir, normalized_dir.replace('/', os.sep)) if normalized_dir else trans_dir
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{base_name}.bean")

    @staticmethod
    def get_bean_relative_path(original_filename, relative_dir=""):
        """获取bean文件相对于 trans/ 目录的相对路径（POSIX 格式）

        Args:
            original_filename: 原始文件名（不带路径）
            relative_dir: 相对于 trans/ 的子目录（POSIX 或系统分隔符），默认为空

        Returns:
            str: 如 "Test/202505_alipay.bean"，位于 trans/ 根目录时为 "202505_alipay.bean"
        """
        base_name = os.path.splitext(original_filename)[0]
        normalized_dir = BeanFileManager._normalize_relative_path(relative_dir)
        if normalized_dir:
            return f"{normalized_dir}/{base_name}.bean"
        return f"{base_name}.bean"

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
    def get_reconciliation_bean_path(user_or_username):
        """获取对账文件路径（trans/reconciliation.bean）
        
        Args:
            user_or_username: User 对象或 username 字符串
            
        Returns:
            trans/reconciliation.bean 文件的完整路径
        """
        trans_dir = os.path.join(BeanFileManager.get_user_assets_path(user_or_username), 'trans')
        return os.path.join(trans_dir, 'reconciliation.bean')

    @staticmethod
    def ensure_reconciliation_bean_included(user_or_username):
        """确保 trans/main.bean 包含 reconciliation.bean
        
        如果 trans/main.bean 中还没有 include "reconciliation.bean"，
        则自动添加。
        
        Args:
            user_or_username: User 对象或 username 字符串
        """
        BeanFileManager.add_bean_to_trans_main(user_or_username, 'reconciliation.bean')

    @staticmethod
    def init_user_bean_structure(user_or_username):
        """初始化完整的用户账本文件结构（幂等操作）
        
        创建以下结构：
        - 用户资产目录
        - main.bean（主账本入口文件）
        - trans/ 目录
        - trans/main.bean（交易记录入口文件）
        
        Args:
            user_or_username: User 对象或 username 字符串
        """
        # 确保用户目录存在
        BeanFileManager.ensure_user_assets_dir(user_or_username)
        
        # 确保主 main.bean 文件存在
        BeanFileManager.ensure_main_bean(user_or_username)
        
        # 确保 trans/main.bean 文件存在
        BeanFileManager.ensure_trans_main_bean(user_or_username)
        
        logger.info(f"初始化用户账本文件结构完成: {user_or_username}")

    @staticmethod
    def ensure_trans_main_bean(user_or_username):
        """确保 trans/main.bean 文件存在（幂等操作）
        
        如果文件不存在，创建带有注释头的空文件。
        
        Args:
            user_or_username: User 对象或 username 字符串
        """
        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)
        
        # 确保 trans 目录存在
        trans_dir = os.path.dirname(trans_main_path)
        os.makedirs(trans_dir, exist_ok=True)
        
        # 如果文件不存在，创建它
        if not os.path.exists(trans_main_path):
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.write("; Trans directory - Auto-generated includes\n")
                f.write("; This file is automatically generated by the Beancount-Trans\n\n")
            logger.debug(f"创建 trans/main.bean 文件: {trans_main_path}")

    @staticmethod
    def ensure_main_bean(user_or_username):
        """确保 main.bean 文件存在并包含 trans/main.bean（幂等操作）
        
        如果文件不存在，创建带有标准模板的文件。
        # 如果文件存在但不包含 trans/main.bean，添加 include 语句。
        
        Args:
            user_or_username: User 对象或 username 字符串
        """
        # 获取用户名（用于模板）
        if hasattr(user_or_username, 'username'):
            username = user_or_username.username
        else:
            username = user_or_username
        
        main_bean_path = BeanFileManager.get_main_bean_path(user_or_username)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(main_bean_path), exist_ok=True)

        # 如果文件不存在，创建它
        if not os.path.exists(main_bean_path):
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
            logger.debug(f"创建 main.bean 文件: {main_bean_path}")
        # else:
        #     # 确保 main.bean 包含 include "trans/main.bean"
        #     with open(main_bean_path, 'r', encoding='utf-8') as f:
        #         content = f.read()

        #     # 检查是否包含 include "trans/main.bean"
        #     trans_main_pattern = re.compile(r'^\s*include\s*"trans/main\.bean"\s*$', re.MULTILINE)
        #     if not trans_main_pattern.search(content):
        #         # 如果不存在，添加到文件末尾
        #         with open(main_bean_path, 'a', encoding='utf-8') as f:
        #             if not content.endswith('\n'):
        #                 f.write('\n')
        #             f.write('include "trans/main.bean"\n')
        #         logger.debug(f"在 main.bean 中添加 include \"trans/main.bean\"")

    @staticmethod
    def create_bean_file(user_or_username, filename, relative_dir=""):
        """
        文件上传时创建对应的{{filename}}.bean文件
        :param user_or_username: User 对象或 username 字符串
        :param filename: 原始文件名（不带路径）
        :param relative_dir: 相对于 trans/ 的子目录（POSIX 或系统分隔符），默认为空
        :return: .bean文件相对于 trans/ 的相对路径（如 "Test/202505_alipay.bean"）
        """
        bean_path = BeanFileManager.get_bean_file_path(user_or_username, filename, relative_dir)
        BeanFileManager.ensure_user_assets_dir(user_or_username)

        if not os.path.exists(bean_path):
            with open(bean_path, 'w', encoding='utf-8') as f:
                pass  # 创建空文件

        return BeanFileManager.get_bean_relative_path(filename, relative_dir)

    @staticmethod
    def add_bean_to_trans_main(user_or_username, bean_relative_path):
        """向 trans/main.bean 添加 include 语句
        
        Args:
            user_or_username: User 对象或 username 字符串
            bean_relative_path: 相对于 trans/ 的.bean文件路径（如 "202505_alipay.bean" 或 "Test/202505_alipay.bean"）
        """
        # 确保 trans/main.bean 文件存在
        BeanFileManager.ensure_trans_main_bean(user_or_username)

        # 统一为 POSIX 分隔符（Beancount 要求 include 使用 "/"）
        bean_relative_path = BeanFileManager._normalize_relative_path(bean_relative_path)
        
        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)

        # 读取现有内容
        with open(trans_main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 构建include语句（相对trans目录）
        include_line = f'include "{bean_relative_path}"\n'
        include_pattern = re.compile(rf'^\s*include\s*"{re.escape(bean_relative_path)}"\s*$')

        # 检查是否已存在
        found = any(include_pattern.match(line) for line in lines)
        
        if not found:
            # 在文件末尾添加include语句
            # 确保最后一行有换行符
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(include_line)
            
            # 写入更新后的内容
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            logger.debug(f"在 trans/main.bean 中添加 include: {bean_relative_path}")

    @staticmethod
    def remove_bean_from_trans_main(user_or_username, bean_relative_path):
        """从 trans/main.bean 删除 include 语句
        
        Args:
            user_or_username: User 对象或 username 字符串
            bean_relative_path: 相对于 trans/ 的.bean文件路径（如 "202505_alipay.bean" 或 "Test/202505_alipay.bean"）
        """
        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)

        # 如果文件不存在，无需操作
        # if not os.path.exists(trans_main_path):
        #     return

        # 统一为 POSIX 分隔符（Beancount 要求 include 使用 "/"）
        bean_relative_path = BeanFileManager._normalize_relative_path(bean_relative_path)

        # 读取现有内容
        with open(trans_main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 构建匹配模式
        include_pattern = re.compile(rf'^\s*include\s*"{re.escape(bean_relative_path)}"\s*$')

        # 过滤掉匹配的行
        new_lines = [line for line in lines if not include_pattern.match(line)]

        # 如果内容有变化，写入文件
        if len(new_lines) != len(lines):
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.debug(f"从 trans/main.bean 中移除 include: {bean_relative_path}")

    # # 向后兼容的别名方法
    # @staticmethod
    # def update_main_bean_include(user_or_username, bean_filename=None, action='add'):
    #     """
    #     向后兼容方法：重定向到 ensure_main_bean
        
    #     注意：bean_filename 和 action 参数在此方法中不再使用，保留仅为了向后兼容
    #     """
    #     logger.warning("update_main_bean_include 已弃用，请使用 ensure_main_bean")
    #     BeanFileManager.ensure_main_bean(user_or_username)

    # @staticmethod
    # def update_trans_main_bean_include(user_or_username, bean_filename, action='add'):
    #     """
    #     向后兼容方法：重定向到 add_bean_to_trans_main 或 remove_bean_from_trans_main
        
    #     Args:
    #         user_or_username: User 对象或 username 字符串
    #         bean_filename: .bean文件名（如 "202505_alipay.bean"）
    #         action: 'add' 或 'remove'
    #     """
    #     logger.warning("update_trans_main_bean_include 已弃用，请使用 add_bean_to_trans_main 或 remove_bean_from_trans_main")
    #     if action == 'add':
    #         BeanFileManager.add_bean_to_trans_main(user_or_username, bean_filename)
    #     elif action == 'remove':
    #         BeanFileManager.remove_bean_from_trans_main(user_or_username, bean_filename)

    @staticmethod
    def delete_bean_file(user_or_username, bean_relative_path):
        """删除对应的.bean文件（从trans目录）

        Args:
            user_or_username: User 对象或 username 字符串
            bean_relative_path: 相对于 trans/ 的.bean文件路径
        """
        bean_path = BeanFileManager._resolve_trans_path(user_or_username, bean_relative_path)
        if os.path.exists(bean_path):
            os.remove(bean_path)
        # 清理遗留的空父目录（不会删除 trans/ 本身）
        BeanFileManager._cleanup_empty_dirs(user_or_username, os.path.dirname(bean_path))

    @staticmethod
    def clear_bean_file(user_or_username, bean_relative_path):
        """清空对应的.bean文件内容（保留文件）

        Args:
            user_or_username: User 对象或 username 字符串
            bean_relative_path: 相对于 trans/ 的.bean文件路径
        """
        bean_path = BeanFileManager._resolve_trans_path(user_or_username, bean_relative_path)
        if os.path.exists(bean_path):
            with open(bean_path, 'w', encoding='utf-8') as f:
                f.write('')  # 清空内容

    @staticmethod
    def _rewrite_include_prefix(user_or_username, old_prefix, new_prefix):
        """重写 trans/main.bean 中指定目录前缀的 include 路径

        Args:
            user_or_username: User 对象或 username 字符串
            old_prefix: 原目录前缀（POSIX，如 "Test"）
            new_prefix: 新目录前缀（POSIX，可为 "" 表示 trans/ 根目录）
        """
        if not old_prefix:
            return

        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)
        if not os.path.exists(trans_main_path):
            return

        with open(trans_main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        prefix = f"{old_prefix}/"
        replacement = f"{new_prefix}/" if new_prefix else ""
        include_pattern = re.compile(
            rf'^(\s*include\s*"){re.escape(prefix)}([^"]*)(")(\s*)$'
        )

        def replace_include(match):
            return f"{match.group(1)}{replacement}{match.group(2)}{match.group(3)}{match.group(4)}"

        new_lines = [include_pattern.sub(replace_include, line) for line in lines]

        if new_lines != lines:
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.debug(f"重写 trans/main.bean 中的 include 前缀: {old_prefix} -> {new_prefix}")

    @staticmethod
    def _remove_includes_by_prefix(user_or_username, prefix_dir):
        """移除 trans/main.bean 中指向指定目录（及其子目录）的 include 语句

        Args:
            user_or_username: User 对象或 username 字符串
            prefix_dir: 目录前缀（POSIX，如 "Test"）
        """
        if not prefix_dir:
            return

        trans_main_path = BeanFileManager.get_trans_main_bean_path(user_or_username)
        if not os.path.exists(trans_main_path):
            return

        with open(trans_main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        include_pattern = re.compile(rf'^\s*include\s*"{re.escape(prefix_dir)}/[^"]+"\s*$')
        new_lines = [line for line in lines if not include_pattern.match(line)]

        if len(new_lines) != len(lines):
            with open(trans_main_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.debug(f"从 trans/main.bean 中移除目录 include: {prefix_dir}")

    @staticmethod
    def move_bean_file(user_or_username, old_rel_path, new_rel_path):
        """移动 trans/ 下的.bean文件，并同步更新 trans/main.bean 的 include

        Args:
            user_or_username: User 对象或 username 字符串
            old_rel_path: 原文件相对于 trans/ 的路径
            new_rel_path: 新文件相对于 trans/ 的路径

        Returns:
            bool: 源文件不存在时返回 False，移动成功返回 True

        Raises:
            FileExistsError: 目标文件已存在（不覆盖）
        """
        old_abs_path = BeanFileManager._resolve_trans_path(user_or_username, old_rel_path)
        new_abs_path = BeanFileManager._resolve_trans_path(user_or_username, new_rel_path)

        if not os.path.exists(old_abs_path):
            return False
        if os.path.exists(new_abs_path):
            raise FileExistsError(f"目标bean文件已存在: {new_rel_path}")

        # 创建目标父目录并移动文件
        os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)
        shutil.move(old_abs_path, new_abs_path)

        # 同步更新 trans/main.bean
        BeanFileManager.remove_bean_from_trans_main(user_or_username, old_rel_path)
        BeanFileManager.add_bean_to_trans_main(user_or_username, new_rel_path)

        # 清理原位置遗留的空目录（不会删除 trans/ 本身）
        BeanFileManager._cleanup_empty_dirs(user_or_username, os.path.dirname(old_abs_path))
        return True

    @staticmethod
    def move_bean_dir(user_or_username, old_rel_dir, new_rel_dir):
        """移动 trans/ 下的目录，并重写 trans/main.bean 中对应的 include 路径

        Args:
            user_or_username: User 对象或 username 字符串
            old_rel_dir: 原目录相对于 trans/ 的路径（POSIX），不可为空
            new_rel_dir: 新目录相对于 trans/ 的路径（POSIX），为空表示移动到 trans/ 根目录

        Returns:
            bool: 源目录不存在时返回 False，移动成功返回 True

        Raises:
            ValueError: old_rel_dir 为空（不允许移动 trans/ 根目录）
            FileExistsError: 目标目录已存在（不合并、不覆盖）
        """
        old_norm_dir = BeanFileManager._normalize_relative_path(old_rel_dir)
        new_norm_dir = BeanFileManager._normalize_relative_path(new_rel_dir)

        if not old_norm_dir:
            raise ValueError("old_rel_dir 不能为空，不允许移动 trans/ 根目录")

        old_abs_dir = BeanFileManager._resolve_trans_path(user_or_username, old_norm_dir)

        if not os.path.isdir(old_abs_dir):
            return False

        if new_norm_dir:
            new_abs_dir = BeanFileManager._resolve_trans_path(user_or_username, new_norm_dir)
            if os.path.exists(new_abs_dir):
                raise FileExistsError(f"目标bean目录已存在: {new_norm_dir}")

            # 创建目标父目录并移动整个目录树
            os.makedirs(os.path.dirname(new_abs_dir), exist_ok=True)
            shutil.move(old_abs_dir, new_abs_dir)
        else:
            # 目标为 trans/ 根目录：将目录内容上移，再删除空目录
            trans_dir = BeanFileManager._resolve_trans_path(user_or_username, "")
            for entry in os.listdir(old_abs_dir):
                shutil.move(os.path.join(old_abs_dir, entry), os.path.join(trans_dir, entry))
            os.rmdir(old_abs_dir)

        # 重写 trans/main.bean 中的 include 前缀
        BeanFileManager._rewrite_include_prefix(user_or_username, old_norm_dir, new_norm_dir)
        return True

    @staticmethod
    def delete_bean_dir(user_or_username, rel_dir):
        """删除 trans/ 下的整个目录，并移除 trans/main.bean 中对应的 include

        Args:
            user_or_username: User 对象或 username 字符串
            rel_dir: 相对于 trans/ 的目录路径（POSIX），为空时不执行任何操作

        Returns:
            bool: rel_dir 为空或目录不存在时返回 False，删除成功返回 True
        """
        norm_dir = BeanFileManager._normalize_relative_path(rel_dir)
        if not norm_dir:
            return False

        target_dir = BeanFileManager._resolve_trans_path(user_or_username, norm_dir)
        if not os.path.isdir(target_dir):
            return False

        shutil.rmtree(target_dir)

        # 移除 trans/main.bean 中指向该目录的 include 语句
        BeanFileManager._remove_includes_by_prefix(user_or_username, norm_dir)
        return True

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
