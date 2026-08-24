"""微信账单 init 策略：兼容 CSV 与 xlsx 导出（元数据行数可能变化）。"""
import io
from pathlib import Path

import pandas as pd
import pytest

from project.apps.translate.services.init.strategies.wechat_init_strategy import WeChatPayInitStrategy
from project.utils.file import convert_df_to_csv_bytes

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "sample_files"
SAMPLE_CSV = FIXTURES / "完整测试_微信.csv"
COLLECT_XLSX = Path("/home/daihaorui/桌面/Syncthing/Bill/03_微信账单测试/微信_Collect.xlsx")


def _init_from_csv_bytes(data: bytes):
    return WeChatPayInitStrategy().init(io.StringIO(data.decode("utf-8-sig")))


def _init_from_xlsx(path: Path):
    df = pd.read_excel(path, header=None, dtype=str).fillna("")
    csv_bytes = convert_df_to_csv_bytes(df)
    return _init_from_csv_bytes(csv_bytes)


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
        if not COLLECT_XLSX.exists():
            pytest.skip("collect xlsx missing")
        records = _init_from_xlsx(COLLECT_XLSX)
        assert len(records) >= 2
        assert records[0]["transaction_time"].startswith("2026-07-")
        assert all(
            WeChatPayInitStrategy._DATETIME_PATTERN.match(r["transaction_time"])
            for r in records
        )

    def test_identifier_accepts_xlsx_title_row(self):
        assert WeChatPayInitStrategy.identifier("微信支付账单明细")
        assert WeChatPayInitStrategy.identifier(WeChatPayInitStrategy.HEADER_MARKER)
