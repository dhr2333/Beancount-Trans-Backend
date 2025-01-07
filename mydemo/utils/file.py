import os
import tempfile
import PyPDF2
import chardet
import pandas as pd

from mydemo.utils.exceptions import UnsupportedFileTypeError, DecryptionError
from translate.utils import get_card_number
from translate.views.BOC_Debit import boc_debit_pdf_convert_to_string, boc_debit_string_convert_to_csv, boc_debit_sourcefile_identifier
from translate.views.ICBC_Debit import icbc_debit_pdf_convert_to_csv, icbc_debit_sourcefile_identifier
from translate.views.CMB_Credit import cmb_credit_pdf_convert_to_csv, cmb_credit_sourcefile_identifier
from translate.views.CCB_Debit import ccb_debit_string_convert_to_csv, ccb_debit_xls_convert_to_string, ccb_debit_sourcefile_identifier

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')

if settings_module == 'conf.prod':
    from conf.prod import *
elif settings_module == 'conf.develop':
    from conf.develop import *
else:
    from mydemo.settings import *

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
        "cycle.bean",
        "event.bean",
        "income.bean",
        "invoice.bean",
        "price.bean"
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
include "cycle.bean"
include "event.bean"
include "income.bean"
include "invoice.bean"
include "price.bean"'''
    dir_path = os.path.split(file_path)[0]  # 获取账单的绝对路径，例如 */Beancount-Trans/Beancount-Trans-Assets/2023
    dir_name = os.path.basename(dir_path)
    if not os.path.isdir(dir_path):  # 判断年份账单是否存在，若不存在则创建目录并在main.bean中include该目录
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
        file_path = os.path.join(os.path.dirname(BASE_DIR), "Beancount-Trans-Assets", year, f"{month}-expenses.bean")
        init_project_file(file_path)
        with open(file_path, mode='a') as file:
            file.write(content)
    except IOError as e:
        print(f"Failed to write to file: {e}")


def file_convert_to_csv(file, password=None):
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
            raise DecryptionError("Decryption failed", 401)
        
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


def read_and_write(reader,writer):
    import csv
    
    reader = csv.reader(reader)
    writer = csv.writer(writer)
    for row in reader:
        writer.writerow(row)