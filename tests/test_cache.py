from pathlib import Path
from modules.cache import ProgressCache


def test_progress_cache_init_default(tmp_path, monkeypatch):
    """Test ProgressCache initialization with default parameters."""
    # Monkeypatch the current working directory so the default
    # cache/progress.json is created in tmp_path
    monkeypatch.chdir(tmp_path)

    cache = ProgressCache()

    assert cache.cache_file == Path('cache/progress.json')
    assert cache.cache_file.parent.exists()
    assert cache.cache_file.parent.is_dir()


def test_progress_cache_init_custom_path(tmp_path):
    """Test ProgressCache initialization with a custom cache file path."""
    custom_path = tmp_path / "my_custom_dir" / "my_progress.json"

    cache = ProgressCache(cache_file=str(custom_path))

    assert cache.cache_file == custom_path
    assert cache.cache_file.parent.exists()
    assert cache.cache_file.parent.is_dir()
    assert cache.cache_file.parent.name == "my_custom_dir"


def test_progress_cache_init_existing_dir(tmp_path):
    """Test ProgressCache initialization when the parent directory already exists."""
    custom_dir = tmp_path / "existing_dir"
    custom_dir.mkdir()
    custom_path = custom_dir / "progress.json"

    # This shouldn't raise an error because of exist_ok=True
    cache = ProgressCache(cache_file=str(custom_path))

    assert cache.cache_file == custom_path
    assert cache.cache_file.parent.exists()


def test_progress_cache_init_path_object(tmp_path):
    """Test ProgressCache initialization when passing a pathlib.Path object."""
    custom_path = tmp_path / "path_dir" / "progress.json"

    cache = ProgressCache(cache_file=custom_path)

    assert cache.cache_file == custom_path
    assert cache.cache_file.parent.exists()


def test_progress_cache_init_nested_dirs(tmp_path):
    """Test ProgressCache initialization with deeply nested directories to verify parents=True."""
    nested_path = tmp_path / "deep" / "nested" / "dir" / "progress.json"

    cache = ProgressCache(cache_file=str(nested_path))

    assert cache.cache_file == nested_path
    assert cache.cache_file.parent.exists()
    assert cache.cache_file.parent.name == "dir"
    assert cache.cache_file.parent.parent.name == "nested"
