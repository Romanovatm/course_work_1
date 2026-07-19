from datetime import datetime

from pandas import DataFrame

from src.reports import spending_by_category
from src.services import cashback, open_file_transactions, search, search_by_mobile_number
from src.utils import find_project_root
from src.views import json_file

item = open_file_transactions(f"{find_project_root()}/data/operations.xlsx")


def main(date: str, transactions: DataFrame, user_str: str, category: str) -> None:
    """Функция, объединяющая логику программы"""
    json_file(date)
    date_obj = datetime.strptime(date, "%d.%m.%Y")
    cashback(transactions, date_obj.year, date_obj.month)
    search(user_str)
    search_by_mobile_number()
    spending_by_category(transactions, category, date)


if __name__ == "__main__":
    main("5.11.2019", item, "магнит", "Фастфуд")
