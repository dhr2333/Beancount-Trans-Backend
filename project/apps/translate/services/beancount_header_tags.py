"""Beancount 交易首行标签解析（忽略引号字符串内的 #）。"""
import re
from typing import List, Tuple

HEADER_TAG_TOKEN_RE = re.compile(r'#\S+')
VALID_SOURCE_TAG_PATH_RE = re.compile(r'^[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-]+)*$')


def is_valid_beancount_tag_path(path: str) -> bool:
    """账单原始 #tag 是否为合法 Beancount 标签路径（不含中文、括号等）。"""
    return bool(VALID_SOURCE_TAG_PATH_RE.match(path))


def find_header_tags_outside_quotes(line: str) -> List[Tuple[int, int, str]]:
    """返回首行中引号外的标签：(start, end, path_without_hash)。"""
    tags: List[Tuple[int, int, str]] = []
    in_quote = False
    i = 0
    length = len(line)
    while i < length:
        ch = line[i]
        if ch == '"':
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote and ch == '#':
            match = HEADER_TAG_TOKEN_RE.match(line, i)
            if match:
                tags.append((match.start(), match.end(), match.group()[1:]))
                i = match.end()
                continue
        i += 1
    return tags


def header_line_has_tags_outside_quotes(line: str) -> bool:
    return bool(find_header_tags_outside_quotes(line))


def strip_header_tags_outside_quotes(line: str) -> str:
    """移除首行引号外的 #tag，保留引号内文本。"""
    parts: List[str] = []
    in_quote = False
    i = 0
    length = len(line)
    while i < length:
        ch = line[i]
        if ch == '"':
            parts.append('"')
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote and ch == '#':
            match = HEADER_TAG_TOKEN_RE.match(line, i)
            if match:
                i = match.end()
                continue
        parts.append(ch)
        i += 1
    return re.sub(r' +', ' ', ''.join(parts)).rstrip()


def replace_header_tags_outside_quotes(line: str, tag_paths: List[str]) -> str:
    """将首行引号外标签替换为 tag_paths 对应的 #path 列表。"""
    base = strip_header_tags_outside_quotes(line)
    if not tag_paths:
        return base
    tag_str = ' '.join(f'#{path}' for path in tag_paths)
    return f'{base} {tag_str}'.rstrip()
