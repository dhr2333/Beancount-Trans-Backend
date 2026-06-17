"""将 BQL 结果表中的账户路径附注为「描述（路径）」。"""


def _format_account_display(account_path: str, description: str) -> str:
    return f'{description}（{account_path}）'


def enrich_bql_result_text(result_text: str, path_map: dict[str, str]) -> str:
    """将结果文本中出现的账户路径替换为「描述（路径）」。"""
    if not path_map or not result_text:
        return result_text

    placeholders: dict[str, str] = {}
    enriched = result_text
    index = 0
    for account_path in sorted(path_map, key=len, reverse=True):
        description = path_map[account_path]
        if not description:
            continue
        placeholder = f'\x00ACC{index}\x00'
        index += 1
        placeholders[placeholder] = _format_account_display(account_path, description)
        enriched = enriched.replace(account_path, placeholder)

    for placeholder, display in placeholders.items():
        enriched = enriched.replace(placeholder, display)

    return enriched
