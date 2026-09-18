"""
Synthetic site_metrics generation, shared by the seed script and the
site-creation endpoint.

No real satellite/remote-sensing pipeline exists for the hackathon (see
README's documented trade-offs), so every site's monthly carbon/biodiversity/
NDVI history is plausible-looking synthetic data: gently increasing carbon
sequestration, a seasonally-noisy biodiversity index, and NDVI in the
0.3-0.8 range. Sites created via the map's draw-a-polygon flow get this
generated for them immediately so their analytics charts aren't empty.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timezone


def month_starts_back(n: int, from_date: date | None = None) -> list[date]:
    """Return `n` month-start dates, oldest first, ending at the current month.

    Implemented with plain calendar arithmetic (no python-dateutil dependency).
    """
    anchor = (from_date or datetime.now(timezone.utc).date()).replace(day=1)
    result = []
    for months_back in range(n - 1, -1, -1):
        total_months = anchor.year * 12 + (anchor.month - 1) - months_back
        year, month0 = divmod(total_months, 12)
        result.append(date(year, month0 + 1, 1))
    return result


def generate_metrics_for_site(
    site_type: str, rng: random.Random | None = None
) -> list[dict]:
    """Generate 12 months of gently-trending, seasonally-noisy metrics."""
    rng = rng or random.Random()
    months = month_starts_back(12)

    base_carbon = rng.uniform(80, 200)  # starting carbon stock (tons)
    monthly_carbon_gain = rng.uniform(1.5, 4.0)

    base_biodiversity = (
        rng.uniform(45, 65) if site_type == "carbon" else rng.uniform(55, 75)
    )
    base_ndvi = rng.uniform(0.45, 0.6)

    rows = []
    for i, month in enumerate(months):
        seasonal_phase = 2 * math.pi * (month.month - 1) / 12

        carbon_tons = base_carbon + monthly_carbon_gain * i + rng.uniform(-1.5, 1.5)

        biodiversity_index = (
            base_biodiversity + 8 * math.sin(seasonal_phase) + rng.uniform(-3, 3)
        )
        biodiversity_index = max(0.0, min(100.0, biodiversity_index))

        ndvi = (
            base_ndvi + 0.12 * math.sin(seasonal_phase + 0.5) + rng.uniform(-0.03, 0.03)
        )
        ndvi = max(0.3, min(0.8, ndvi))

        rows.append(
            {
                "date": month,
                "carbon_tons": round(carbon_tons, 2),
                "biodiversity_index": round(biodiversity_index, 2),
                "ndvi": round(ndvi, 3),
            }
        )
    return rows
