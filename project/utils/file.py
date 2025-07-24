# project/utils/file.py
import io
import os
import tempfile
import PyPDF2
import chardet
import pandas as pd
import hashlib

from project.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from translate.utils import get_card_number
from translate.views.BOC_Debit import boc_debit_pdf_convert_to_string, boc_debit_string_convert_to_csv, boc_debit_sourcefile_identifier
from translate.views.ICBC_Debit import icbc_debit_pdf_convert_to_csv, icbc_debit_sourcefile_identifier
from translate.views.CMB_Credit import cmb_credit_pdf_convert_to_csv, cmb_credit_sourcefile_identifier
from translate.views.CCB_Debit import ccb_debit_string_convert_to_csv, ccb_debit_xls_convert_to_string, ccb_debit_sourcefile_identifier
from django.conf import settings


SUPPORTED_EXTENSIONS = ['.csv', '.xls', '.xlsx', '.pdf']

def init_project_file(file_path):
    file_list = [
        "00.bean",
        "01-expenses.bean",
        "02-expenses.bean",
        "03-expenses.bean",
        "04-expenses.bean",
        "05-expenses.bean",
        "06-expenses.bean",
        "07-expenses.bean",
        "08-expenses.bean",
        "09-expenses.bean",
        "10-expenses.bean",
        "11-expenses.bean",
        "12-expenses.bean",
        "budget.bean",
        "cycle.bean",
        "event.bean",
        "income.bean",
        "note.bean",
        "price.bean",
        "query.bean",
        "securities.bean",
        "time.bean"
    ]
    insert_contents = '''include "01-expenses.bean"
include "02-expenses.bean"
include "03-expenses.bean"
include "04-expenses.bean"
include "05-expenses.bean"
include "06-expenses.bean"
include "07-expenses.bean"
include "08-expenses.bean"
include "09-expenses.bean"
include "10-expenses.bean"
include "11-expenses.bean"
include "12-expenses.bean"
include "budget.bean"
include "cycle.bean"
include "event.bean"
include "income.bean"
include "note.bean"
include "price.bean"
include "query.bean"
include "securities.bean"
include "time.bean"'''
    dir_path = os.path.split(file_path)[0]  # 获取账单的绝对路径，例如 */Beancount-Trans/Beancount-Trans-Assets/2023
    dir_name = os.path.basename(dir_path)
    if not os.path.isdir(dir_path):  # 判断年份账单是否存在，若不存在则创建目录
        # 如果存在模板目录则根据模板目录创建对应文件，模板目录名称为"2022_template",并将保留模板目录中"00.bean"的内容复制到新创建的"00.bean"中
        if os.path.isdir(os.path.join(os.path.dirname(dir_path), "template")):
            template_dir = os.path.join(os.path.dirname(dir_path), "template")
            os.makedirs(dir_path)
            insert_include = f'\ninclude "{dir_name}/00.bean"'
            main_file = os.path.dirname(dir_path) + "/main.bean"
            with open(main_file, 'a') as main:
                main.write(insert_include)
            template_00_path = os.path.join(template_dir, "00.bean")
            with open(template_00_path, 'r') as template_00:
                template_content = template_00.read()
            createfile = os.path.join(dir_path, "00.bean")
            with open(createfile, 'w') as f:
                f.write(template_content)
            for file_name in file_list:
                createfile = os.path.join(dir_path, file_name)
                open(createfile, 'w').close()
        else:
            # 如果没有模板目录则按照硬编码格式创建
            os.makedirs(dir_path)
            insert_include = f'\ninclude "{dir_name}/00.bean"'
            main_file = os.path.dirname(dir_path) + "/main.bean"
            with open(main_file, 'a') as main:
                main.write(insert_include)
            for file_name in file_list:  # 该for循环用于创建按年划分的所有文件
                createfile = os.path.join(dir_path, file_name)
                open(createfile, 'w').close()
                if file_name == "00.bean":  # 00.bean文件会include其他文件来让beancount正确识别
                    with open(createfile, 'w') as f:
                        f.write(insert_contents)


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


def write_entry_to_file(content):
    """将条目写入相应的beancount文件"""
    try:
        year = content[0:4]
        month = content[5:7]
        file_path = os.path.join(os.path.dirname(settings.BASE_DIR), "Beancount-Trans-Assets", year, f"{month}-expenses.bean")
        init_project_file(file_path)
        with open(file_path, mode='a') as file:
            file.write(content)
    except IOError as e:
        print(f"Failed to write to file: {e}")


def convert_to_csv_bytes(file, password=None):
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

def handle_excel(file):
    string_content = ccb_debit_xls_convert_to_string(file)
    for row in string_content:
        if any(pd.notnull(item) and ccb_debit_sourcefile_identifier in str(item) for item in row):
            convert_content = ccb_debit_string_convert_to_csv(string_content)
            return convert_content.encode()

def handle_pdf(file, password):
    pdf = PyPDF2.PdfReader(file)
    if pdf.is_encrypted:
        if not pdf.decrypt(password):
            raise DecryptionError("PDF解密失败", 401)

    content = extract_text_from_pdf(pdf)

    # 根据内容处理PDF
    if cmb_credit_sourcefile_identifier in content:
        return cmb_credit_pdf_convert_to_csv(content).encode()
    elif boc_debit_sourcefile_identifier in content:
        card_number = get_card_number(content, boc_debit_sourcefile_identifier)
        string_content = boc_debit_pdf_convert_to_string(file, password)
        return boc_debit_string_convert_to_csv(string_content, card_number).encode()
    elif icbc_debit_sourcefile_identifier in content:
        card_number = get_card_number(content, icbc_debit_sourcefile_identifier)
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
        
# def read_and_write(reader,writer):
#     import csv

#     reader = csv.reader(reader)
#     writer = csv.writer(writer)
#     for row in reader:
#         writer.writerow(row)

def generate_file_hash(file):
    """生成文件哈希值"""
    hasher = hashlib.sha256()
    for chunk in file.chunks():
        hasher.update(chunk)
    file.seek(0)  # 重置文件指针
    return hasher.hexdigest()

# from django.core.files.uploadedfile import InMemoryUploadedFile

# def create_in_memory_file(original_name: str, content: bytes) -> InMemoryUploadedFile:
#     """创建内存中的CSV文件对象"""
#     # 创建新文件名
#     base_name, _ = os.path.splitext(original_name)
#     csv_name = f"{base_name}_converted.csv"
    
#     # 创建内存文件
#     file = io.BytesIO(content)
#     file.seek(0)
    
#     return InMemoryUploadedFile(
#         file=file,
#         field_name='csv_file',
#         name=csv_name,
#         content_type='text/csv',
#         size=len(content),
#         charset='utf-8'
#     )

def create_text_stream(original_name: str, content: bytes) -> io.StringIO:
    """创建UTF-8编码的文本流对象"""
    # 将字节内容解码为字符串
    content_str = content.decode('utf-8', errors='ignore')
    
    # 创建内存文本流
    text_stream = io.StringIO(content_str)
    text_stream.name = f"{os.path.splitext(original_name)[0]}_converted.csv"
    return text_stream