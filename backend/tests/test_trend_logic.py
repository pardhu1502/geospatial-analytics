"""
Unit tests for the `_direction` helper in app/api/routers/sites.py, which
underlies the "improving"/"declining"/"stable" trend classification used by
`GET /sites/{site_id}/analytics/summary`. Pure function, no DB needed.
"""

from app.api.routers.sites import _direction


def test_direction_detects_clear_improvement():
    assert _direction(first_avg=10.0, second_avg=20.0) == 1


def test_direction_detects_clear_decline():
    assert _direction(first_avg=20.0, second_avg=10.0) == -1


def test_direction_treats_small_noise_as_stable():
    # 0.5% change is well under the 2% threshold.
    assert _direction(first_avg=100.0, second_avg=100.5) == 0


def test_direction_handles_near_zero_baseline_without_dividing_by_zero():
    # Should not raise, and a small absolute change near zero is "stable".
    assert _direction(first_avg=0.0, second_avg=0.0000001) == 0
