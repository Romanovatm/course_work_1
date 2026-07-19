from datetime import datetime
from unittest.mock import patch

import pandas as pd

from src import reports


def test_spending_by_category_with_explicit_date(report_transactions: pd.DataFrame) -> None:
    """Отчёт включает обе границы трёхмесячного периода и только расходы категории."""
    result = reports.spending_by_category(report_transactions, "Связь", "15.04.2026")

    pd.testing.assert_frame_equal(result, pd.DataFrame({"Категория": ["Связь"], "Сумма": [300]}))


def test_spending_by_category_uses_current_date(report_transactions: pd.DataFrame) -> None:
    """Без даты концом периода служит текущий момент."""

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 15)

    with patch("src.reports.datetime", FixedDateTime):
        result = reports.spending_by_category(report_transactions, "Связь")

    assert result.iloc[0].to_dict() == {"Категория": "Связь", "Сумма": 300}
