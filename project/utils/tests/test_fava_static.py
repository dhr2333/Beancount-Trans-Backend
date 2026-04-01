import pytest
from project.utils.fava_static import parse_fava_static_user_map


def test_parse_json():
    m = parse_fava_static_user_map('{"a":"http://h:1","b":"http://h:2/"}')
    assert m == {"a": "http://h:1", "b": "http://h:2"}


def test_parse_comma():
    m = parse_fava_static_user_map("alice=http://x:5001,bob=http://x:5002")
    assert m == {"alice": "http://x:5001", "bob": "http://x:5002"}


def test_parse_empty():
    assert parse_fava_static_user_map("") == {}
    assert parse_fava_static_user_map("   ") == {}
