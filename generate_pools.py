"""
Script to generate and save driver and customer pools.

Before running the simulator, run this script to create a set of
drivers and customers and save them as JSON files. This way, the same
people appear across all generated ride records.

Run this once before generating any historical data:

    python generate_pools.py

Then pass the saved files when generating rides:

    python data_generator.py historical --count 25000 --format csv \\
        --duration 2026-01-01:2026-02-01 \\
        --driver-pool data/pools/driver_pool_500.json \\
        --customer-pool data/pools/customer_pool_5000.json

Pool sizes are set by driver_pool_size and customer_pool_size in
RuntimeConfig (generator/config.py).
"""

import json
from dataclasses import asdict
from pathlib import Path

from generator.config import DEFAULT_CONFIG
from generator.pool import build_driver_pool, build_customer_pool


# Output directory for all saved pool files.
POOLS_DIR = Path("data/pools")


def run() -> None:
    """
    Build driver and customer pools and save them to disk as JSON files.

    Pool sizes are read from DEFAULT_CONFIG.

    Output files:
        data/pools/driver_pool_{size}.json
        data/pools/customer_pool_{size}.json
    """
    config = DEFAULT_CONFIG

    # Create the output directory if it does not already exist.
    POOLS_DIR.mkdir(parents=True, exist_ok=True)


    # --- Build pools ---

    print(f"Building driver pool   : {config.driver_pool_size:,} drivers...")
    driver_pool = build_driver_pool(config.driver_pool_size)

    print(f"Building customer pool : {config.customer_pool_size:,} customers...")
    customer_pool = build_customer_pool(config.customer_pool_size)


    # --- Save to files ---

    driver_path   = POOLS_DIR / f"driver_pool_{config.driver_pool_size}.json"
    customer_path = POOLS_DIR / f"customer_pool_{config.customer_pool_size}.json"

    with driver_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(d) for d in driver_pool], f, ensure_ascii=False, indent=2)

    with customer_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in customer_pool], f, ensure_ascii=False, indent=2)


    # --- Summary ---

    print()
    print("=" * 50)
    print("Pools saved successfully.")
    print("=" * 50)
    print(f"Driver pool   : {len(driver_pool):,} drivers   → {driver_path}")
    print(f"Customer pool : {len(customer_pool):,} customers → {customer_path}")


if __name__ == "__main__":
    run()
