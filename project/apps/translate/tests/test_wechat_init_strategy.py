"""微信账单 init 策略：兼容 CSV 与 xlsx 导出（元数据行数可能变化）。"""
import io
from pathlib import Path

import pandas as pd
import pytest

from project.apps.translate.services.init.strategies.wechat_init_strategy import WeChatPayInitStrategy
from project.utils.file import convert_df_to_csv_bytes

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "sample_files"
SAMPLE_CSV = FIXTURES / "完整测试_微信.csv"


def _init_from_csv_bytes(data: bytes):
    return WeChatPayInitStrategy().init(io.StringIO(data.decode("utf-8-sig")))


def _wechat_xlsx_like_df():
    """模拟微信 xlsx 导出：元数据 + 分隔行 + 表头 + 两条交易。"""
    empty = [""] * 10
    return pd.DataFrame([
        ["微信支付账单明细", *empty],
        ["微信昵称：[测试]", *empty],
        ["", *empty],
        ["----------------------微信支付账单明细列表--------------------", *empty],
        [
            "交易时间", "交易类型", "交易对方", "商品", "收/支",
            "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注",
        ],
        [
            "2026-07-01 10:00:00", "商户消费", "商店A", "商品A", "支出",
            "¥10.00", "零钱", "支付成功", "1001", "m1", "/",
        ],
        [
            "2026-07-02 11:00:00", "商户消费", "商店B", "商品B", "支出",
            "¥20.00", "零钱", "支付成功", "1002", "m2", "/",
        ],
    ])


class TestWeChatPayInitStrategy:
    def test_sample_csv_skips_separator_and_parses_data(self):
        if not SAMPLE_CSV.exists():
            pytest.skip("sample csv missing")
        with open(SAMPLE_CSV, encoding="utf-8-sig") as f:
            records = WeChatPayInitStrategy().init(f)
        assert len(records) > 30
        assert records[0]["transaction_time"] == "2023-01-01 10:49:54"
        assert all(
            "微信支付账单明细列表" not in r["transaction_time"]
            for r in records
        )

    def test_xlsx_export_skips_separator_row(self):
        records = _init_from_csv_bytes(convert_df_to_csv_bytes(_wechat_xlsx_like_df()))
        assert len(records) >= 2
        assert records[0]["transaction_time"].startswith("2026-07-")
        assert all(
            WeChatPayInitStrategy._DATETIME_PATTERN.match(r["transaction_time"])
            for r in records
        )

    def test_identifier_accepts_xlsx_title_row(self):
        assert WeChatPayInitStrategy.identifier("微信支付账单明细")
        assert WeChatPayInitStrategy.identifier(WeChatPayInitStrategy.HEADER_MARKER)
