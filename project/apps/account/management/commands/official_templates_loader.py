# project/apps/account/management/commands/official_templates_loader.py
"""
从 project/fixtures/official_templates/ 目录加载官方模板 JSON 数据。
文件不存在或解析失败时返回 None，由调用方决定是否回退到内嵌数据。
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

OFFICIAL_TEMPLATES_DIR_NAME = "official_templates"
ACCOUNT_JSON = "account.json"
MAPPING_EXPENSE_JSON = "mapping_expense.json"
MAPPING_INCOME_JSON = "mapping_income.json"
MAPPING_ASSETS_JSON = "mapping_assets.json"

# BASE_DIR 在 settings 中为 backend 根目录，project 在其下
PROJECT_DIR = Path(settings.BASE_DIR) / "project"
FIXTURES_OFFICIAL_DIR = PROJECT_DIR / "fixtures" / OFFICIAL_TEMPLATES_DIR_NAME


def get_official_templates_dir() -> Path:
    """返回官方模板 JSON 所在目录路径。"""
    return FIXTURES_OFFICIAL_DIR


def _load_json_file(path: Path) -> Optional[dict]:
    """读取 JSON 文件，失败返回 None 并打日志。"""
    if not path.exists():
        logger.debug("官方模板文件不存在: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("加载官方模板 JSON 失败 %s: %s", path, e)
        return None


def _validate_account_item(item: dict) -> bool:
    """校验账户模板项必有 account_path。"""
    if not isinstance(item, dict):
        return False
    return isinstance(item.get("account_path"), str) and len(item["account_path"].strip()) > 0


def load_official_account_data() -> Optional[dict]:
    """
    从 account.json 加载官方账户模板数据。
    返回格式: {"name", "description", "version", "update_notes", "items": [{...}]}
    文件不存在或校验失败返回 None。
    """
    path = FIXTURES_OFFICIAL_DIR / ACCOUNT_JSON
    data = _load_json_file(path)
    if not data or "items" not in data:
        return None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    for i, item in enumerate(items):
        if not _validate_account_item(item):
            logger.warning("account.json items[%d] 缺少有效 account_path，已跳过", i)
            return None
    return data


def _validate_mapping_expense_item(item: dict) -> bool:
    return isinstance(item, dict) and isinstance(item.get("key"), str) and len(item["key"].strip()) > 0


def _validate_mapping_income_item(item: dict) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("key"), str)
        and len(item["key"].strip()) > 0
        and isinstance(item.get("account"), str)
        and len(item["account"].strip()) > 0
    )


def _validate_mapping_assets_item(item: dict) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("key"), str)
        and len(item["key"].strip()) > 0
        and isinstance(item.get("full"), str)
        and isinstance(item.get("account"), str)
        and len(item["account"].strip()) > 0
    )


def load_official_mapping_data(template_type: str) -> Optional[dict]:
    """
    从 mapping_<type>.json 加载官方映射模板数据。
    template_type 为 'expense' | 'income' | 'assets'。
    返回格式: {"name", "description", "version", "update_notes", "items": [{...}]}
    文件不存在或校验失败返回 None。
    """
    filename_map = {
        "expense": MAPPING_EXPENSE_JSON,
        "income": MAPPING_INCOME_JSON,
        "assets": MAPPING_ASSETS_JSON,
    }
    validator_map = {
        "expense": _validate_mapping_expense_item,
        "income": _validate_mapping_income_item,
        "assets": _validate_mapping_assets_item,
    }
    if template_type not in filename_map:
        return None
    path = FIXTURES_OFFICIAL_DIR / filename_map[template_type]
    data = _load_json_file(path)
    if not data or "items" not in data:
        return None
    items = data.get("items")
    if not isinstance(items, list):
        return None
    validate = validator_map[template_type]
    for i, item in enumerate(items):
        if not validate(item):
            logger.warning(
                "mapping_%s.json items[%d] 校验失败，已跳过",
                template_type,
                i,
            )
            return None
    return data


def load_all_official_templates_data() -> dict[str, Any]:
    """
    一次性加载所有官方模板 JSON（若存在）。
    返回: {"account": dict | None, "mapping_expense": dict | None, "mapping_income": dict | None, "mapping_assets": dict | None}
    """
    return {
        "account": load_official_account_data(),
        "mapping_expense": load_official_mapping_data("expense"),
        "mapping_income": load_official_mapping_data("income"),
        "mapping_assets": load_official_mapping_data("assets"),
    }
