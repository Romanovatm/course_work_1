import json
import logging

import pandas as pd
from pandas import DataFrame

from src.utils import find_project_root

logger = logging.getLogger("service")
file_handler = logging.FileHandler(f"{find_project_root()}/logs/service.log", "w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)


def open_file_transactions(file_path: str) -> DataFrame:
    """
    Функция открывает и читает excel файл
    """

    df = pd.read_excel(file_path)
    return df


def cashback(data: DataFrame, year: int, month: int) -> str:
    """
    Функция рассчитывает выгодные категории кэшбэка за указанный месяц года
    """

    logger.debug("Начало работы функции")
    data["Дата операции"] = pd.to_datetime(data["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    logger.debug("Задан формат даты операции")

    filter_date = data[
        (data["Дата операции"].dt.year == year)
        & (data["Дата операции"].dt.month == month)
        & (data["Статус"] == "OK")
        & (data["Сумма платежа"] < 0)
        & (data["Кэшбэк"])
        > 0
    ]
    logger.debug("Применены фильтры к таблице")

    grouped = filter_date.groupby("Категория")[["Кэшбэк"]].sum().to_dict()
    key_cashback = grouped["Кэшбэк"]
    logger.debug("Посчитан кэшбэк для каждой уникальной категории")

    new_format_dict = {key: int(value) for key, value in key_cashback.items()}
    sorted_key_cashback = dict(sorted(new_format_dict.items(), key=lambda x: x[1], reverse=True))
    logger.debug("Перевод значений в int и сортировка по убыванию")

    json_string = json.dumps(sorted_key_cashback, ensure_ascii=False, indent=4)
    logger.info("Успешное завершение функции, перевод словаря в JSON строку")

    return json_string


def search(user_str: str) -> str:
    """
    Функция ищет строку пользователя в колонках "Описание" и "Категория"
    и возвращает результат в виде JSON-строки
    """

    file = pd.read_excel(f"{find_project_root()}/data/operations.xlsx")
    query = user_str.lower()

    mask = file["Описание"].astype(str).str.lower().str.contains(query, na=False) | file["Категория"].astype(
        str
    ).str.lower().str.contains(query, na=False)

    filtered_file = file[mask]

    return filtered_file.to_json(orient="records", force_ascii=False, indent=4)


def search_by_mobile_number() -> str:
    """
    Функция находит все транзакции, у которых в колонке 'Описание' содержится
    мобильный телефонный номер, и возвращает их в формате JSON.
    """

    file = pd.read_excel(f"{find_project_root()}/data/operations.xlsx")

    mobile_number_pattern = r"(?:\+7|8)[\s-]?\(?9\d{2}\)?[\s\d-]{7,11}"

    mask = file["Описание"].astype(str).str.contains(mobile_number_pattern, regex=True, na=False)

    filtered_file = file[mask]

    return filtered_file.to_json(orient="records", force_ascii=False, indent=4)
