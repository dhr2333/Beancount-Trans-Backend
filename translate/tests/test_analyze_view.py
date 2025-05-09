from unittest.mock import patch
import pytest
import os
import tempfile
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from textwrap import dedent
from django.core.management import call_command


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ALIPAY_TEST_FILE = os.path.join(TEST_DATA_DIR, "单条测试_支付宝.csv")

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """全局数据库初始化"""
    with django_db_blocker.unblock():
        # 加载所有需要的 Fixtures
        call_command('loaddata', 'users.json')
        call_command('loaddata', 'expenses.json')
        call_command('loaddata', 'incomes.json')
        call_command('loaddata', 'assets.json')


@pytest.fixture
def loaded_expenses(django_db_setup):
    """返回已加载的 Expense 数据查询集"""
    from translate.models import Expense
    return Expense.objects.all()

def normalize_string(s):
    return "\n".join(line.strip() for line in s.strip().splitlines())

@pytest.mark.django_db
@pytest.mark.usefixtures("django_db_setup")
def test_alipay_end_to_end_processing(client, loaded_expenses):
    """支付宝账单端到端处理测试"""
    # 验证 Fixture 数据加载成功
    assert loaded_expenses.count() >= 2  # 根据你的测试数据调整
    assert loaded_expenses.filter(key="蜜雪冰城").exists()
    # 1. 读取真实测试文件内容
    with open(ALIPAY_TEST_FILE, "rb") as f:
        original_content = f.read()

    # 2. 创建真实临时文件
    with tempfile.NamedTemporaryFile(delete=False) as real_temp:
        real_temp.write(original_content)
        temp_path = real_temp.name
        encoding = "gb2312"

    try:
        # 3. 创建上传文件对象
        uploaded_file = SimpleUploadedFile(
            name="alipay_test.csv",
            content=original_content,
            content_type="text/csv"
        )

        # 4. 构建完整请求参数
        post_data = {
            "password": "",
            "isCSVOnly": "false",
            "balance": "false",
            "write": "false",
            "cmb_credit_ignore": "false",
            "boc_debit_ignore": "false",
            "csrfmiddlewaretoken": "mock_csrf_token"
        }

        # 5. 请求头配置
        headers = {
            "HTTP_X_CSRFTOKEN": "mock_csrf_token",
            "HTTP_AUTHORIZATION": "Bearer mock_valid_token"
        }

        # 6. 模拟关键函数
        with patch("translate.views.view.get_token_user_id") as mock_user_id, \
             patch("translate.views.view.create_temporary_file") as mock_create_temp, \
             patch("translate.views.view.file_convert_to_csv") as mock_convert:

            # 设置返回值
            mock_user_id.return_value = 1
            mock_create_temp.return_value = (real_temp, encoding)  # 返回真实文件对象
            mock_convert.return_value = original_content

            # 7. 发送请求
            response = client.post(
                reverse("trans"),
                data={**post_data, "trans": uploaded_file},
                **headers
            )

        # 8. 验证响应状态
        assert response.status_code == 200
        result = response.json()

        # 9. 验证输出内容
        expected_output = dedent("""
            2023-02-22 * "瑞安市青松大药房有限公司" "医保支付(不含自费)"
                time: "21:03:03"
                uuid: "20230222998605612887"
                status: "ALiPay - 支付成功"
                Expenses:Health:Medical 0.00 CNY
                Assets:Savings:Web:AliPay -0.00 CNY

            2023-05-18 * "北京卡路里科技有限公司" "连续包月"
                time: "12:34:02"
                uuid: "2023051822001499861457916613"
                status: "ALiPay - 交易成功"
                Expenses:Culture:Subscription 19.00 CNY
                Assets:Savings:Web:AliFund -19.00 CNY
            """).strip()

        # 处理可能的列表响应
        if isinstance(result, list):
            actual_content = "".join(result)
        else:
            actual_content = result  # 假设是字符串或其他结构

        # 在断言前标准化字符串
        normalized_actual = normalize_string(actual_content)
        normalized_expected = normalize_string(expected_output)

        assert normalized_actual == normalized_expected

    finally:
        # 10. 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
