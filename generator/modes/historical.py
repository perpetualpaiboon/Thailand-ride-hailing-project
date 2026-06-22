"""
Historical data generation mode.

Generate a batch of ride records within a specified date range
and writes the output to a file inside 'data/historical_data/'.

The output filename is automatically generated from the provided date range
(e.g. historical_20260401_20260430.json).

Supported output formats:
    json:   Writes records as a JSON array
    csv:    Writes records as CSV rows with headers

Usage:
    python data_generator.py historical --count 10000 --format json --duration 2026-04-01:2026-04-30
    python data_generator.py historical --count 5000 --format csv --duration 2026-03-01:2026-03-31
"""

import csv
import json
from datetime import datetime

from settings.storage import HISTORICAL_DATA_DIR
from generator import generate_ride_record
from generator.config import RuntimeConfig
from generator.pool import build_driver_pool, build_customer_pool, load_driver_pool, load_customer_pool


def _parse_duration(duration_str: str) -> tuple[datetime, datetime]:
    """
    Parses a --duration string into start and end datetime objects.

    Args:
        duration_str (str): Date range in YYYY-MM-DD:YYYY-MM-DD fmt.

    Returns:
        tuple[datetime, datetime]: The parsed start and end dates.

    Raises:
        ValueError: If the fmt is invalid or start date is not earlier than end date.
    """
    try:
        start_str, end_str = duration_str.split(":")
        start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid --duration fmt. Expected YYYY-MM-DD:YYYY-MM-DD, got: {duration_str!r}"
        )
    if start_date >= end_date:
        raise ValueError("Start date must be before end date.")
    return start_date, end_date


def _build_output_path(start_date: datetime, end_date: datetime, fmt: str) -> Path:
    """
    Build the output file path for historical data generation.

    The filename is automatically generated using the provided date range
    and output fmt.

    Args:
        start_date (datetime):  Start date of the generated dataset.
        end_date (datetime):    End date of the generated dataset.
        fmt (str):              Output file format (e.g. "json", "csv").

    Returns:
        Path:   Full path to the output file.
    """
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")
    return HISTORICAL_DATA_DIR / f"historical_{start}_{end}.{fmt}"


def _print_progress(current: int, total: int) -> None:
    """
    Print generation progress to the terminal.

    Progress updates are displayed every 100 generated records
    and once again when generation is complete.

    Args:
        current (int):  Number of records generated so far.
        total (int):    Total number of records to generate.
    """
    if current % 10 == 0 or current == total:
        print(f"  {current:,}/{total:,} records written", flush=True)


def _write_json(f, total: int, config: RuntimeConfig, driver_pool, customer_pool) -> None:
    """
    Generate ride records and write them as a JSON array.

    Args:
        f:                          Open file object used for writing.
        total (int):                Total number of records to generate.
        config (RuntimeConfig):     Runtime configuration used during record generation.
        driver_pool (list[Driver]):     Pre-built driver pool.
        customer_pool (list[Customer]): Pre-built customer pool.
    """
    f.write("[\n")
    for i in range(1, total + 1):
        record = generate_ride_record(config, driver_pool, customer_pool)
        comma = (
            ","
            if i < total else ""
        )
        f.write("  " + json.dumps(record, ensure_ascii=False) + comma + "\n")
        _print_progress(i, total)
    f.write("]\n")


def _write_csv(f, total: int, config: RuntimeConfig, driver_pool, customer_pool) -> None:
    """
    Generate ride records and write them as CSV rows.

    CSV column headers are extracted from the keys of the first generated record.

    Args:
        f:                          Open file object used for writing.
        total (int):                Total number of records to generate.
        config (RuntimeConfig):     Runtime configuration used during record generation.
        driver_pool (list[Driver]):     Pre-built driver pool.
        customer_pool (list[Customer]): Pre-built customer pool.
    """
    writer = None
    for i in range(1, total + 1):
        record = generate_ride_record(config, driver_pool, customer_pool)
        if writer is None:
            writer = csv.DictWriter(
                f,
                fieldnames=record.keys(),
                # Put quotation marks around every field to prevent commas inside
                # address fields from accidentally creating new columns.
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
        writer.writerow(record)
        _print_progress(i, total)


def run(args) -> None:
    """
    Execute historical data generation and write the output to a file.

    This function:
        - Parses the requested date range
        - Creates the runtime configuration
        - Builds the output file path
        - Generates ride records
        - Writes the records in the selected format

    Args:
        args:   Parsed command-line interface (CLI) arguments containing:
                - format
                - count
                - duration
    """
    fmt = args.format
    total = args.count

    start_date, end_date = _parse_duration(args.duration)
    config = RuntimeConfig(debug=False, start_date=start_date, end_date=end_date)
    output_path = _build_output_path(start_date, end_date, fmt)

    # Load pools from file if paths provided, otherwise build in memory.
    if args.driver_pool:
        driver_pool = load_driver_pool(args.driver_pool)
        driver_pool_source = f"Loaded from file  : {args.driver_pool}"
    else:
        driver_pool = build_driver_pool(config.driver_pool_size)
        driver_pool_source = "Built in memory"

    if args.customer_pool:
        customer_pool = load_customer_pool(args.customer_pool)
        customer_pool_source = f"Loaded from file  : {args.customer_pool}"
    else:
        customer_pool = build_customer_pool(config.customer_pool_size)
        customer_pool_source = "Built in memory"

    # Create the output directory if it does not exist yet.
    HISTORICAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Date range    : {start_date.date()} to {end_date.date()}")
    print(f"Records       : {total:,}")
    print(f"Driver pool   : {len(driver_pool):,} drivers - {driver_pool_source}")
    print(f"Customer pool : {len(customer_pool):,} customers - {customer_pool_source}")
    print(f"Output        : {output_path}")

    with output_path.open("w", encoding="utf-8", newline="") as f:
        if fmt == "json":
            _write_json(f, total, config, driver_pool, customer_pool)
        elif fmt == "csv":
            _write_csv(f, total, config, driver_pool, customer_pool)

    print("Done.")
