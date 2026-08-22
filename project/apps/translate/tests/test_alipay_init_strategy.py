import io
from pathlib import Path

import pytest

from project.apps.translate.services.init.strategies.alipay_init_strategy import AlipayInitStrategy

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "sample_files"
NEW_ALIPAY_CSV = FIXTURES_DIR / "202607_alipay.csv"
OLD_ALIPAY_CSV = FIXTURES_DIR / "完整测试_支付宝.csv"


def _load_sample(path: Path, encoding: str) -> io.StringIO:
    content = path.read_text(encoding=encoding)
    stream = io.StringIO(content)
    stream.readline()
    return stream


@pytest.mark.parametrize(
    "path,encoding,expected_count,first_time,first_amount",
    [
        (
            NEW_ALIPAY_CSV,
            "gb18030",
            38,
            "2026-07-30 17:48:14",
            1.00,
        ),
        (
            OLD_ALIPAY_CSV,
            "utf-8",
            80,
            "2025-12-18 18:16:25",
            15.12,
        ),
    ],
)
def test_alipay_init_after_readline(path, encoding, expected_count, first_time, first_amount):
    """模拟 InitializeBillStep 先 readline 再 init 的场景。"""
    if not path.exists():
        pytest.skip(f"sample file missing: {path}")

    stream = _load_sample(path, encoding)
    records = AlipayInitStrategy().init(stream)

    assert len(records) == expected_count
    assert records[0]["transaction_time"] == first_time
    assert records[0]["amount"] == first_amount
    assert records[0]["bill_identifier"] == "alipay"
