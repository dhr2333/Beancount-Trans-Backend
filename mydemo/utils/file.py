import os
import tempfile

import chardet


def create_temporary_file(file_name):
    """Create a temporary file and return its path."""
    content = file_name.read()
    encodeing = chardet.detect(content)['encoding']
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(content)
    temp.flush()
    return temp, encodeing


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
        "price.bean",
        "time.bean"
    ]
    insert_contents = '''include "01-expenses.bean"
include "02-expenses.bean"
include "03-expenses.bean"
include "04-expenses.bean"
include "05-expenses.bean"
include "06-expenses.bean"
include "07-expenses.bean"
include "09-expenses.bean"
include "10-expenses.bean"
include "11-expenses.bean"
include "12-expenses.bean"
include "cycle.bean"
include "event.bean"
include "income.bean"
include "invoice.bean"
include "price.bean"
include "time.bean"'''
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
