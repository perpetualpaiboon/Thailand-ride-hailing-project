"""
Generate mode 

Generates a specified number of  ride records 
and prints outputs to the terminal as a JSON.

This mode is intended for debugging, and inspecting
generated ride data directly from the terminal.

Usage:
    python data_generator.py generate
    python data_generator.py generate --count 10
    python data_generator.py generate --count 10 --debug
"""
import json

from generator import generate_ride_record
from generator.config import RuntimeConfig
from generator.pool import build_driver_pool, build_customer_pool


def run(args):
    """
    Execute data generation and print outputs as JSON.

    Args:
        args:   Parsed command-line interface (CLI) arguments containing:
                - count
                - debug
    """
    config        = RuntimeConfig(debug=args.debug, num_records=args.count)
    driver_pool   = build_driver_pool(config.driver_pool_size)
    customer_pool = build_customer_pool(config.customer_pool_size)

    records = []
    for _ in range(config.num_records):
        records.append(generate_ride_record(config, driver_pool, customer_pool))

    print(json.dumps(records, indent=2, ensure_ascii=False))

