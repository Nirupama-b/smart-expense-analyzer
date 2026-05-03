"""Unit tests for the linear-trend forecast in the analytics router.

We exercise the public `/api/analytics/forecast` endpoint via FastAPI's
TestClient, with `_get_admin_supabase` patched to return mocked rows
and the `get_current_user` dependency overridden to skip JWT validation.
"""

from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from middleware.auth import get_current_user


def _mock_supabase(rows):
    """Build a Supabase client mock whose query chain resolves to *rows*."""
    mock = MagicMock()
    chain = (
        mock.table.return_value.select.return_value.eq.return_value
        .gte.return_value.lte.return_value
    )
    chain.execute.return_value = MagicMock(data=rows)
    return mock


def _client_with_user(user_id: str = "test-user") -> TestClient:
    """Return a TestClient with auth bypassed."""
    app.dependency_overrides[get_current_user] = lambda: user_id
    return TestClient(app)


def teardown_function(_):
    """Clear dependency overrides between tests."""
    app.dependency_overrides.clear()


class TestForecastEndpoint:
    def test_returns_zero_predictions_when_no_history(self):
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase([])):
            resp = client.get("/api/analytics/forecast?months_ahead=3")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all(p["predicted_spend"] == 0 for p in data)

    def test_flat_history_predicts_flat_future(self):
        # Three identical months → slope ~0, intercept = 100.
        rows = [
            {"amount": 100, "date": "2026-01-15"},
            {"amount": 100, "date": "2026-02-15"},
            {"amount": 100, "date": "2026-03-15"},
        ]
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase(rows)):
            resp = client.get("/api/analytics/forecast?months_ahead=2")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        for p in data:
            assert abs(p["predicted_spend"] - 100.0) < 0.01

    def test_increasing_history_predicts_growth(self):
        rows = [
            {"amount": 100, "date": "2026-01-15"},
            {"amount": 200, "date": "2026-02-15"},
            {"amount": 300, "date": "2026-03-15"},
        ]
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase(rows)):
            resp = client.get("/api/analytics/forecast?months_ahead=1")

        data = resp.json()
        # Trend slope = 100/month; next point ~ 400.
        assert data[0]["predicted_spend"] >= 300

    def test_predicted_spend_is_never_negative(self):
        # Steeply declining history would otherwise yield a negative forecast.
        rows = [
            {"amount": 1000, "date": "2026-01-15"},
            {"amount": 500, "date": "2026-02-15"},
            {"amount": 50, "date": "2026-03-15"},
        ]
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase(rows)):
            resp = client.get("/api/analytics/forecast?months_ahead=6")

        for p in resp.json():
            assert p["predicted_spend"] >= 0

    def test_rejects_out_of_range_months_ahead(self):
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase([])):
            resp = client.get("/api/analytics/forecast?months_ahead=99")
        assert resp.status_code == 422


class TestSummaryEndpoint:
    def test_summary_with_no_expenses_returns_zero(self):
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase([])):
            resp = client.get("/api/analytics/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_spend"] == 0
        assert body["expense_count"] == 0
        assert body["top_category"] is None

    def test_summary_computes_top_category(self):
        rows = [
            {"amount": 30, "category_id": 1, "categories": {"name": "Dining"}},
            {"amount": 20, "category_id": 1, "categories": {"name": "Dining"}},
            {"amount": 100, "category_id": 2, "categories": {"name": "Groceries"}},
        ]
        client = _client_with_user()
        with patch("routers.analytics._get_admin_supabase", return_value=_mock_supabase(rows)):
            resp = client.get("/api/analytics/summary?budget=200")

        body = resp.json()
        assert body["total_spend"] == 150.0
        assert body["top_category"] == "Groceries"
        assert body["budget_utilization"] == 75.0
