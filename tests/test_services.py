import json
from unittest.mock import patch

import pandas as pd

from src import services


def test_open_file_transactions_delegates_to_pandas() -> None:
    """Функция чтения возвращает DataFrame, полученный от pandas."""
    expected = pd.DataFrame({"value": [1]})
    with patch("src.services.pd.read_excel", return_value=expected) as mock_read:
        assert services.open_file_transactions("operations.xlsx") is expected
        mock_read.assert_called_once_with("operations.xlsx")


def test_cashback_filters_groups_sorts_and_serializes(service_transactions: pd.DataFrame) -> None:
    """Кэшбэк учитывает только успешные расходы выбранного месяца и сортирует итог."""
    result = json.loads(services.cashback(service_transactions.copy(), 2026, 5))

    assert result == {"Еда": 10, "Транспорт": 5}


def test_search_is_case_insensitive_and_checks_two_columns(service_transactions: pd.DataFrame) -> None:
    """Поиск не зависит от регистра и работает по описанию и категории."""
    with patch("src.services.pd.read_excel", return_value=service_transactions):
        by_description = json.loads(services.search("КАФЕ"))
        by_category = json.loads(services.search("транспорт"))

    assert len(by_description) == 2
    assert [row["Категория"] for row in by_category] == ["Транспорт"]


def test_search_by_mobile_number_returns_only_phone_rows(service_transactions: pd.DataFrame) -> None:
    """Регулярное выражение выделяет операции с российским мобильным номером."""
    with patch("src.services.pd.read_excel", return_value=service_transactions):
        result = json.loads(services.search_by_mobile_number())

    assert len(result) == 1
    assert result[0]["Категория"] == "Транспорт"
