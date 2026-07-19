from pathlib import Path

import pytest

from src.utils import find_project_root


def test_find_project_root_finds_marker_in_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Корень определяется по маркеру и при запуске из вложенной директории."""
    project = tmp_path / "project"
    nested = project / "one" / "two"
    nested.mkdir(parents=True)
    (project / "pyproject.toml").touch()
    monkeypatch.chdir(nested)

    assert find_project_root() == project


def test_find_project_root_accepts_single_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Строковый маркер поддерживается так же, как кортеж маркеров."""
    (tmp_path / "custom.marker").touch()
    monkeypatch.chdir(tmp_path)

    assert find_project_root("custom.marker") == tmp_path


def test_find_project_root_raises_without_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """При отсутствии всех маркеров функция сообщает понятную ошибку."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="Не удалось найти корень проекта"):
        find_project_root(("missing-one", "missing-two"))
