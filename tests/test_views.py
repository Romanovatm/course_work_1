import json
from datetime import datetime
from unittest.mock import Mock, mock_open, patch

import pandas as pd
import pytest
import requests

from src import views


@pytest.mark.parametrize(
    "hour, expected",
    [(6, "Доброе утро"), (11, "Доброе утро"), (12, "Добрый день"),
     (17, "Добрый день"), (18, "Добрый вечер"), (22, "Добрый вечер"),
     (23, "Доброй ночи"), (5, "Доброй ночи")],
)
def test_greet_user(hour: int, expected: str) -> None:
    """Проверяем приветствие на границах каждого временного периода."""
    with patch("src.views.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 1, 1, hour)
        assert views.greet_user() == expected


def test_get_card_info(excel_transactions: pd.DataFrame) -> None:
    """Проверяем группировку расходов по карте и расчёт кэшбэка."""
    with patch("src.views.pd.read_excel", return_value=excel_transactions):
        result = views.get_card_info("31.05.2026")

    assert result == [{"last_digits": "2345.0", "total_spent": 150.12, "cashback": 1.5}]


def test_top_5_transactions(excel_transactions: pd.DataFrame) -> None:
    """Проверяем отбор успешных положительных операций за нужный месяц."""
    with patch("src.views.pd.read_excel", return_value=excel_transactions):
        result = views.top_5_transactions("31.05.2026")

    assert result == [
        {"date": "20.05.2026", "amount": 900.0, "category": "Зарплата", "description": "Доход"}
    ]


def test_get_currency_rates(settings_file) -> None:
    """Проверяем успешный ответ API и пропуск некорректных курсов."""
    response = Mock()
    response.json.return_value = {"rates": {"USD": 0.01, "EUR": 0.02, "ZERO": 0, "TEXT": "bad"}}

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        result = views.get_currency_rates()

    assert result == [{"currency": "USD", "rate": 100.0}, {"currency": "EUR", "rate": 50.0}]


@pytest.mark.parametrize("error", [requests.Timeout(), requests.RequestException("network")])
def test_get_currency_rates_request_errors(error: Exception, settings_file) -> None:
    """Проверяем обработку тайм-аута и общей сетевой ошибки."""
    with patch("builtins.open", settings_file), patch("src.views.requests.get", side_effect=error):
        assert views.get_currency_rates() == []


def test_get_currency_rates_invalid_json(settings_file) -> None:
    """Проверяем обработку ответа, который нельзя разобрать как JSON."""
    response = Mock()
    response.json.side_effect = json.JSONDecodeError("bad", "", 0)

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        assert views.get_currency_rates() == []


def test_get_currency_rates_empty(settings_file) -> None:
    """Проверяем пустой словарь курсов в корректном ответе API."""
    response = Mock()
    response.json.return_value = {"rates": {}}

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        assert views.get_currency_rates() == []


def test_stock_prices(settings_file) -> None:
    """Проверяем преобразование и округление цен акций."""
    response = Mock()
    response.json.return_value = {"AAPL": {"price": "123.456"}, "MSFT": {"price": "99"}}

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        result = views.stock_prices()

    assert result == [{"stock": "AAPL", "price": 123.46}, {"stock": "MSFT", "price": 99.0}]
    response.raise_for_status.assert_called_once()


@pytest.mark.parametrize(
    "error",
    [requests.Timeout(), requests.HTTPError("status"), requests.RequestException("network")],
)
def test_stock_prices_request_errors(error: Exception, settings_file) -> None:
    """Проверяем все предусмотренные сетевые ошибки API акций."""
    response = Mock()
    response.raise_for_status.side_effect = error

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        assert views.stock_prices() == []


def test_stock_prices_invalid_json(settings_file) -> None:
    """Проверяем обработку некорректного JSON с ценами акций."""
    response = Mock()
    response.json.side_effect = json.JSONDecodeError("bad", "", 0)

    with patch("builtins.open", settings_file), patch("src.views.requests.get", return_value=response):
        assert views.stock_prices() == []


def test_json_file() -> None:
    """Проверяем сборку итогового словаря и его запись в JSON-файл."""
    opened = mock_open()

    with (
        patch("src.views.greet_user", return_value="Привет"),
        patch("src.views.get_card_info", return_value=[{"card": "1234"}]),
        patch("src.views.top_5_transactions", return_value=[{"amount": 100}]),
        patch("src.views.get_currency_rates", return_value=[{"currency": "USD"}]),
        patch("src.views.stock_prices", return_value=[{"stock": "AAPL"}]),
        patch("builtins.open", opened),
    ):
        views.json_file("31.05.2026")

    written = json.loads("".join(call.args[0] for call in opened().write.call_args_list))
    assert written["greeting"] == "Привет"
    assert written["cards"] == [{"card": "1234"}]
