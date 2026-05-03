from unittest.mock import MagicMock
import pytest
import numpy as np
from backend.services.forecasting import ForecastingService, MIN_EXPENSES_FOR_FORECAST

def _mock_db(expenses, budget=500.0):
    mock = MagicMock()
    ec = MagicMock(); ec.execute.return_value = MagicMock(data=expenses)
    mock.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value = ec
    bc = MagicMock(); bc.execute.return_value = MagicMock(data={"monthly_budget": budget})
    mock.table.return_value.select.return_value.eq.return_value.single.return_value = bc
    mock.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    return mock

def _expenses(n):
    months = ["2025-10-01","2025-11-01","2025-12-01","2026-01-01","2026-02-01","2026-03-01"]
    return [{"amount": 100.0 + i, "date": months[i % len(months)], "category_id": 1} for i in range(n)]

def test_cold_start_too_few():
    r = ForecastingService(_mock_db(_expenses(3))).get_prediction_for_user("u1")
    assert r["cold_start"] is True and r["predicted_spend"] is None

def test_cold_start_zero():
    r = ForecastingService(_mock_db([])).get_prediction_for_user("u1")
    assert r["cold_start"] is True

def test_cold_start_one_below_threshold():
    r = ForecastingService(_mock_db(_expenses(MIN_EXPENSES_FOR_FORECAST - 1))).get_prediction_for_user("u1")
    assert r["cold_start"] is True

def test_forecast_runs_with_enough_data():
    r = ForecastingService(_mock_db(_expenses(15))).get_prediction_for_user("u1")
    assert r["cold_start"] is False and r["predicted_spend"] is not None

def test_predicted_spend_non_negative():
    r = ForecastingService(_mock_db(_expenses(15))).get_prediction_for_user("u1")
    assert r["predicted_spend"] >= 0

def test_burnout_in_range():
    r = ForecastingService(_mock_db(_expenses(15))).get_prediction_for_user("u1")
    assert 0.0 <= r["burnout_probability"] <= 1.0

def test_required_keys_present():
    r = ForecastingService(_mock_db(_expenses(15))).get_prediction_for_user("u1")
    for k in ("user_id","month","predicted_spend","burnout_probability","budget","generated_at"):
        assert k in r

def test_high_spend_high_burnout():
    e = [{"amount":800.0,"date":f"2023-{(i%12)+1:02d}-01","category_id":1} for i in range(30)]
    r = ForecastingService(_mock_db(e, budget=200.0)).get_prediction_for_user("u1")
    assert r["burnout_probability"] > 0.9

def test_low_spend_low_burnout():
    e = [{"amount":20.0,"date":f"2024-{(i%12)+1:02d}-01","category_id":1} for i in range(20)]
    r = ForecastingService(_mock_db(e, budget=2000.0)).get_prediction_for_user("u1")
    assert r["burnout_probability"] < 0.1

def test_burnout_at_budget_is_half():
    assert abs(ForecastingService._burnout_prob(500.0, 500.0) - 0.5) < 0.01

def test_burnout_zero_budget():
    assert ForecastingService._burnout_prob(100.0, 0.0) == 1.0

def test_burnout_zero_spend():
    assert ForecastingService._burnout_prob(0.0, 500.0) < 0.01
