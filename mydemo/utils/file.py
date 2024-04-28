import os
import tempfile

import PyPDF2
import chardet
from mydemo.utils.exceptions import UnsupportedFileType, DecryptionError
from translate.utils import get_card_number
from translate.views.BOC_Debit import boc_debit_pdf_convert_to_string, boc_debit_string_convert_to_csv, boc_debit_sourcefile_identifier
from translate.views.ICBC_Debit import icbc_debit_pdf_convert_to_csv, icbc_debit_sourcefile_identifier
from translate.views.CMB_Credit import cmb_credit_pdf_convert_to_csv, cmb_credit_sourcefile_identifier
from translate.views.CCB_Debit import ccb_debit_string_convert_to_csv, ccb_debit_xls_convert_to_string, ccb_debit_sourcefile_identifier


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
        raise UnsupportedFileType("当前账单不支持")
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(content)
    temp.flush()
    return temp, encodeing


def file_convert_to_csv(file, password):
    import pandas as pd
    """转换为CSV格式供程序读取解析

    Args:
        file (_type_): _description_
        password (str): PDF文件的密码，如果文件受保护
    """
    # 根据后缀判断传入的文件类型
    _, file_extension = os.path.splitext(file.name)
    if file_extension.lower() == '.csv':
        return file  # <class 'django.core.files.uploadedfile.InMemoryUploadedFile'>
    # 架构
    elif file_extension.lower() == '.xls' or file_extension.lower() == '.xlsx':
        string_content = ccb_debit_xls_convert_to_string(file) 
        for row in string_content:
            for item in row:
                if pd.notnull(item) and ccb_debit_sourcefile_identifier in str(item):
                    convert_content = ccb_debit_string_convert_to_csv(string_content)
                    file = convert_content.encode()
                    return file
    elif file_extension.lower() == '.pdf':
        pdf = PyPDF2.PdfReader(file)
        # 若文件加密，则根据上传的密码进行解密
        if pdf.is_encrypted:
            pdf.decrypt(password)
        try:
            num_pages = len(pdf.pages)
        except PyPDF2.errors.FileNotDecryptedError:
            raise DecryptionError("Decryption failed", 403)
        content = ""
        # 对得到的文本统一存放至变量，为后续判断账单类型做准备；
        for page_num in range(num_pages):
            page = pdf.pages[page_num]
            content += page.extract_text()
        # print("content = ", content)  # 输出所有流水信息，用于判断银行卡
        # content会包含pdf文件的所有内容，找到能明确表明账单归属的文本用于判断所属的银行和卡片类型；
        if cmb_credit_sourcefile_identifier in content:  # 如果匹配到招商银行PDF文件
            convert_content = cmb_credit_pdf_convert_to_csv(content)
            file = convert_content.encode()
            return file
        elif boc_debit_sourcefile_identifier in content:
            card_number = get_card_number(content, boc_debit_sourcefile_identifier)
            string_content = boc_debit_pdf_convert_to_string(file, password)  # 中国银行储蓄卡账单无法通过基础pypdf2读取，需要进行数据处理
            convert_content = boc_debit_string_convert_to_csv(string_content, card_number)
            file = convert_content.encode()
            return file
        elif icbc_debit_sourcefile_identifier in content:
            card_number = get_card_number(content, icbc_debit_sourcefile_identifier)
            convert_content = icbc_debit_pdf_convert_to_csv(file, card_number ,password)
            file = convert_content.encode()
            return file
