import functools
import logging
from typing import Optional, Any, Callable

from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

from src.services import open_file_transactions
from src.utils import find_project_root

logger = logging.getLogger("reports")
file_handler = logging.FileHandler(f"{find_project_root()}/logs/reports.log", "w", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

item = open_file_transactions(f"{find_project_root()}/data/operations.xlsx")

def save_report_to(filename: str) -> Callable:
    """Декоратор сохраняет результат работы функции в файл с указанным именем."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> pd.DataFrame:
            result = func(*args, **kwargs)

            result.to_json(filename, orient="records", force_ascii=False, indent=4)
            print(f"DataFrame успешно записан в файл: {filename}")
            return result
        return wrapper
    return decorator


@save_report_to(f"{find_project_root()}/data/report.json")
def spending_by_category(transactions: pd.DataFrame,
                         category: str,
                         date: Optional[str] = None) -> pd.DataFrame:

    logger.debug("Начало работы функции")
    if date:
        end_date = datetime.strptime(date, "%d.%m.%Y")
        logger.debug("Переданная дата переведена в строку заданного формата")
    else:
        end_date = datetime.now()
        logger.debug("Используется текущая дата")

    start_date = end_date - relativedelta(months=3)
    logger.debug("Задан диапазон дат")

    df = transactions[transactions["Категория"] == category]
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    df = df[(df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)]
    df = df[df["Сумма платежа"] < 0]
    df = df[df["Статус"] == "OK"]
    logger.debug("Применен фильтр к таблице")
    df = abs(df["Сумма платежа"].sum())
    logger.debug("Вычислена общая сумма по категории")

    result_df = pd.DataFrame({
        "Категория": [category],
        "Сумма": [df]})
    logger.info("Успешное выполнение функции")

    return result_df
