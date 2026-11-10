import random
from pathlib import Path

root = Path("company_data")

for dept in ["clients", "contracts"]:
    (root / dept).mkdir(parents=True, exist_ok=True)

    for i in range(1, 11):
        lines = [
            f"{dept};doc{i};{random.randint(1000, 99999)}"
            for _ in range(200)
        ]

        (root / dept / f"report_{i}.csv").write_text(
            "\n".join(lines),
            encoding="utf-8"
        )

print("Тестовые данные созданы в папке company_data/")