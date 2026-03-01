"""Generate mock historical transactions for RiskGuard MVP."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sys

import pandas as pd
from faker import Faker

try:
    from config import settings
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from config import settings


def generate_mock_transactions(record_count: int = 1000) -> pd.DataFrame:
    """Generate a deterministic synthetic transactions dataset."""
    fake = Faker()
    Faker.seed(settings.random_seed)

    users = [f"user_{index:03d}" for index in range(1, 51)]
    cities = [
        "Kuala Lumpur",
        "George Town",
        "Johor Bahru",
        "Ipoh",
        "Kota Kinabalu",
        "Shah Alam",
        "Melaka",
        "Kuching",
    ]

    start = pd.Timestamp("2026-02-01T00:00:00", tz="Asia/Kuala_Lumpur")
    rows: list[dict[str, object]] = []

    for idx in range(record_count):
        user_id = fake.random_element(users)
        amount = round(
            float(
                fake.pydecimal(
                    left_digits=4,
                    right_digits=2,
                    positive=True,
                    min_value=5,
                    max_value=2500,
                )
            ),
            2,
        )
        city = fake.random_element(cities)
        timestamp = start + timedelta(seconds=idx * fake.random_int(min=20, max=300))
        rows.append(
            {
                "transaction_id": f"tx_{idx + 1:05d}",
                "user_id": user_id,
                "amount": amount,
                "city": city,
                "timestamp": timestamp.isoformat(),
            }
        )

    return pd.DataFrame(rows)


def save_mock_transactions(output_path: Path | str = Path("data/mock_transactions.csv")) -> Path:
    """Generate and save synthetic transactions as CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_mock_transactions(record_count=1000)
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    destination = save_mock_transactions()
    print(f"Mock transactions written to: {destination}")
