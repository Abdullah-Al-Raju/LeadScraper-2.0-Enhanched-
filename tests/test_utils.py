import os
import sys

# Add the root directory to the sys.path
parent_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(parent_dir, '..'))
sys.path.insert(0, root_dir)

from modules.utils import truncate_text  # noqa: E402


def test_truncate_text_shorter_than_max():
    text = "Hello world"
    assert truncate_text(text, max_chars=20) == "Hello world"


def test_truncate_text_exact_length():
    text = "Hello world"
    assert truncate_text(text, max_chars=11) == "Hello world"


def test_truncate_text_longer_than_max():
    text = "Hello world"
    assert truncate_text(text, max_chars=5) == "Hello..."


def test_truncate_text_default_max_chars():
    # If max_chars is not provided, it shouldn't truncate short strings
    text = "Hello world"
    assert truncate_text(text) == "Hello world"


def test_truncate_text_empty():
    assert truncate_text("", max_chars=10) == ""
