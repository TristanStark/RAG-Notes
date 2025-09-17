from pathlib import Path

BASE = Path("./data")
(BASE / "images").mkdir(parents=True, exist_ok=True)
print("[init] data/ & data/images ready")
