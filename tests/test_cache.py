import pytest
import json
from pathlib import Path
from datetime import datetime
from modules.cache import ProgressCache

@pytest.fixture
def temp_cache_file(tmp_path):
    return tmp_path / "test_cache" / "progress.json"

@pytest.fixture
def cache(temp_cache_file):
    return ProgressCache(cache_file=str(temp_cache_file))

def test_init_creates_directory(tmp_path):
    cache_file = tmp_path / "new_dir" / "progress.json"
    cache = ProgressCache(cache_file=str(cache_file))
    assert cache_file.parent.exists()
    assert cache_file.parent.is_dir()

def test_save_and_load(cache, temp_cache_file):
    data = {'completed_rows': [1, 2, 3]}
    cache.save(data)

    assert temp_cache_file.exists()

    loaded_data = cache.load()
    assert loaded_data is not None
    assert loaded_data['completed_rows'] == [1, 2, 3]
    assert 'last_updated' in loaded_data

    # Ensure it's valid ISO format
    datetime.fromisoformat(loaded_data['last_updated'])

def test_load_non_existent_file(cache):
    assert cache.load() is None

def test_clear(cache, temp_cache_file):
    data = {'completed_rows': [1, 2, 3]}
    cache.save(data)
    assert temp_cache_file.exists()

    cache.clear()
    assert not temp_cache_file.exists()

def test_clear_non_existent_file(cache, caplog):
    # Should not raise exception
    cache.clear()

def test_exists(cache, temp_cache_file):
    assert not cache.exists()
    cache.save({'test': 'data'})
    assert cache.exists()

def test_get_completed_rows_empty(cache):
    assert cache.get_completed_rows() == []

def test_get_completed_rows_with_data(cache):
    cache.save({'completed_rows': [5, 10, 15]})
    assert cache.get_completed_rows() == [5, 10, 15]

def test_get_completed_rows_missing_key(cache):
    cache.save({'other_data': 'test'})
    assert cache.get_completed_rows() == []

def test_add_completed_row_initial(cache):
    cache.add_completed_row(1)

    data = cache.load()
    assert data is not None
    assert data['completed_rows'] == [1]

def test_add_completed_row_multiple(cache):
    cache.add_completed_row(1)
    cache.add_completed_row(2)
    cache.add_completed_row(5)

    data = cache.load()
    assert data['completed_rows'] == [1, 2, 5]

def test_add_completed_row_duplicate(cache):
    cache.add_completed_row(1)
    cache.add_completed_row(1)

    data = cache.load()
    assert data['completed_rows'] == [1]

def test_add_completed_row_preserves_existing_data(cache):
    cache.save({'other_key': 'value', 'completed_rows': [1]})
    cache.add_completed_row(2)

    data = cache.load()
    assert data['completed_rows'] == [1, 2]
    assert data['other_key'] == 'value'

def test_save_error_handling(cache, monkeypatch):
    def mock_open(*args, **kwargs):
        raise PermissionError("Access denied")

    import builtins
    monkeypatch.setattr(builtins, "open", mock_open)

    # Should not raise
    cache.save({'test': 'data'})

def test_load_error_handling(cache, temp_cache_file, monkeypatch):
    cache.save({'test': 'data'})

    def mock_open(*args, **kwargs):
        raise PermissionError("Access denied")

    import builtins
    monkeypatch.setattr(builtins, "open", mock_open)

    # Should not raise, should return None
    assert cache.load() is None

def test_clear_error_handling(cache, temp_cache_file, monkeypatch):
    cache.save({'test': 'data'})

    def mock_unlink(*args, **kwargs):
        raise PermissionError("Access denied")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    # Should not raise
    cache.clear()
