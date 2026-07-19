import json
import logging
import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import find_project_root

load_dotenv()

logger = logging.getLogger("views")
file_handler = logging.FileHandler(f"{find_project_root()}/logs/views.log", "w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)


def greet_user() -> str:
    """Функция-приветсвие в зависимости от текущего времени"""

    current_hour = datetime.now().hour
    if 6 <= current_hour <= 11:
        return "Доброе утро"
    elif 12 <= current_hour <= 17:
        return "Добрый день"
    elif 18 <= current_hour <= 22:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_card_info(date_str: str) -> list[dict]:
    """
    Функция считывает Excel-файл, фильтрует расходы, группирует их по картам
    и возвращает список словарей json формата {карта: сумма расходов}
    """

    current_date = datetime.strptime(date_str, "%d.%m.%Y")
    start_date = current_date.replace(day=1, hour=0, minute=0, second=0)
    end_date = current_date.replace(hour=23, minute=59, second=59)

    excel_file = pd.read_excel(f"{find_project_root()}/data/operations.xlsx")
    excel_file["Дата операции"] = pd.to_datetime(excel_file["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    excel_file = excel_file[(excel_file["Дата операции"] >= start_date) & (excel_file["Дата операции"] <= end_date)]
    excel_file = excel_file.dropna(subset=["Номер карты", "Сумма платежа"])
    expenses_unique_card = excel_file[excel_file["Сумма платежа"] < 0]
    card_expenses_dict = expenses_unique_card.groupby("Номер карты")["Сумма платежа"].sum().abs().to_dict()

    card_expenses_json = [
        {
            "last_digits": str(elem)[1:],
            "total_spent": round(card_expenses_dict[elem], 2),
            "cashback": round(card_expenses_dict[elem] / 100, 2),
        }
        for elem in card_expenses_dict
    ]

    return card_expenses_json


def top_5_transactions(date_str: str) -> list[dict]:
    """
    Функция считывает Excel-файл и возвращает Топ-5 транзакций по сумме платежа
    """

    current_date = datetime.strptime(date_str, "%d.%m.%Y")
    start_date = current_date.replace(day=1, hour=0, minute=0, second=0)
    end_date = current_date.replace(hour=23, minute=59, second=59)

    excel_file = pd.read_excel(f"{find_project_root()}/data/operations.xlsx")
    excel_file["Дата операции"] = pd.to_datetime(excel_file["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    excel_file = excel_file[(excel_file["Дата операции"] >= start_date) & (excel_file["Дата операции"] <= end_date)]
    excel_file = excel_file.dropna(subset=["Номер карты", "Сумма платежа"])
    excel_file = excel_file[excel_file["Статус"] == "OK"]
    excel_file = excel_file[excel_file["Сумма платежа"] > 0]
    sorted_file = excel_file.sort_values(by="Сумма платежа", ascending=False).to_dict("records")

    sorted_file_json = [
        {
            "date": elem.get("Дата операции").strftime("%d.%m.%Y"),  # type: ignore
            "amount": elem.get("Сумма платежа"),
            "category": elem.get("Категория"),
            "description": elem.get("Описание"),
        }
        for elem in sorted_file[:5]
    ]

    return sorted_file_json


def get_currency_rates() -> list[dict]:
    """
    Функция возвращает результат API-запроса для получения актуальных обменных курсов запрашиваемых
    валют в формате json
    """

    api_key = os.getenv("CURRENCY_API")

    logger.debug("Начало работы функции")
    with open(f"{find_project_root()}/user_settings.json", "r", encoding="utf-8") as f:
        user_settings = json.load(f)
        user_settings = user_settings["user_currencies"]
        user_settings = ",".join(user_settings)
        logger.debug("Успешное открытие json файла, перевод из списка в строку")

    logger.debug("Старт попытки выполнения API запроса")
    try:
        response = requests.get(
            f"https://api.fxratesapi.com/latest?"
            f"api_key={api_key}&base=RUB&currencies={user_settings}&resolution=1d&format=json",
            timeout=10,
        )

        data = response.json()
        logger.debug("Успешное выполнение запроса, перевод в формат JSON")

    except requests.exceptions.Timeout:
        print("Ошибка: Превышено время ожидания ответа от FX Rates API.")
        logger.error("Превышено время ожидания ответа")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Сетевая ошибка при запросе к API: {e}")
        logger.error("Сетевая ошибка")
        return []
    except json.JSONDecodeError:
        print("Ошибка: API вернул некорректный JSON.")
        logger.error("Некорректный файл")
        return []

    rates = data.get("rates", {})

    if not rates:
        print("Предупреждение: API вернул пустой словарь 'rates'.")
        logger.error("API вернул пустой словарь 'rates'")
        return []

    currency_rates = [
        {"currency": rate, "rate": round(1 / rates.get(rate), 2)}
        for rate in rates
        if rates.get(rate) and isinstance(rates.get(rate), (int, float)) and rates.get(rate) != 0
    ]

    logger.info("Функция завершилась успешно")
    return currency_rates


def stock_prices() -> list[dict]:
    """
    Функция возвращает результат API-запроса для получения актуальных котировок запрашиваемых
    акций в формате json
    """

    api_key = os.getenv("STOCK_API")

    with open(f"{find_project_root()}/user_settings.json", "r", encoding="utf-8") as f:
        user_settings = json.load(f)
        user_settings = user_settings["user_stocks"]
        user_settings = ",".join(user_settings)

    try:
        response = requests.get(
            f"https://api.twelvedata.com/price?symbol={user_settings}&apikey={api_key}", timeout=10
        )
        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:
        print("Ошибка: Превышено время ожидания ответа от Twelve Data API.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка API акций (Неверный ответ сервера): {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Сетевая ошибка при запросе котировок акций: {e}")
        return []
    except json.JSONDecodeError:
        print("Ошибка: API акций вернул некорректный JSON.")
        return []

    stock = [{"stock": elem, "price": round(float(data[elem]["price"]), 2)} for elem in data]
    return stock


def json_file(date: str) -> None:
    """
    Функция собирает и записывает в файл готовый json формат главной страницы
    """

    result = {
        "greeting": greet_user(),
        "cards": get_card_info(date),
        "top_transactions": top_5_transactions(date),
        "currency_rates": get_currency_rates(),
        "stock_prices": stock_prices(),
    }
    with open(f"{find_project_root()}/data/main.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
