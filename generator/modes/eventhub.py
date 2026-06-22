"""
Event Hub mode 

Generate and streams ride records to Azure Event Hub.

Connection credentials are loaded from environment variables or a '.env' file.

Supports two modes:
    single:     generates and sends one ride record
    stream:     continuously generate and send ride records at a set interval 
                until interrupted or the requested count is reached

Required environment variables:
    EVENT_HUB_CONNECTION_STR:  Azure Event Hub connection string
    EVENT_HUB_NAME:             Name of the target Event Hub

Usage:
    python data_generator.py eventhub --mode single         
    python data_generator.py eventhub --mode stream
    python data_generator.py eventhub --mode stream --interval 2.0 --count 50
"""

import json
import os
import time

from azure.eventhub import EventData, EventHubProducerClient
from dotenv import load_dotenv

from generator import generate_ride_record
from generator.config import RuntimeConfig
from generator.pool import build_driver_pool, build_customer_pool


def _build_client() -> EventHubProducerClient:
    """
    Creates an Event Hub producer client using credentials from the environment.

    Raises:
        EnvironmentError: If EVENT_HUB_CONNECTION_STR or EVENT_HUB_NAME is not set.
    """
    connection_str  = os.environ.get("EVENT_HUB_CONNECTION_STR")
    hub_name = os.environ.get("EVENT_HUB_NAME")

    if not connection_str  or not hub_name:
        raise EnvironmentError(
            "Missing required environment variables.\n"
            "Ensure EVENT_HUB_CONNECTION_STR and EVENT_HUB_NAME are set in your .env file."
        )
    return EventHubProducerClient.from_connection_string(connection_str , eventhub_name=hub_name)


def _send_one(client: EventHubProducerClient, config: RuntimeConfig, driver_pool, customer_pool) -> str:
    """
    Generates and sends a single ride record to Event Hub.

    Args:
        client (EventHubProducerClient):    Active Event Hub producer client.
        config (RuntimeConfig):             Runtime configuration for record generation.
        driver_pool (list[Driver]):         Pre-built driver pool.
        customer_pool (list[Customer]):     Pre-built customer pool.

    Returns:
        str: The ride_id of the sent record.
    """
    record = generate_ride_record(config, driver_pool, customer_pool)
    event_data_batch = client.create_batch()
    event_data_batch.add(EventData(json.dumps(record, ensure_ascii=False)))
    client.send_batch(event_data_batch)
    return record["ride_id"]


def _run_single(config: RuntimeConfig) -> None:
    """Sends one ride record and prints the result."""
    driver_pool   = build_driver_pool(config.driver_pool_size)
    customer_pool = build_customer_pool(config.customer_pool_size)
    with _build_client() as client:
        ride_id = _send_one(client, config, driver_pool, customer_pool)
        print(f"    Sent: {ride_id}")


def _run_stream(config: RuntimeConfig, interval: float, limit: int) -> None:
    """
    Continuously sends ride records at a fixed interval.

    Args:
        config (RuntimeConfig): Runtime configuration for record generation.
        interval (float):       Seconds to wait between each send.
        limit (int):            Maximum records to send. 0 means run until Ctrl+C.
    """
    driver_pool   = build_driver_pool(config.driver_pool_size)
    customer_pool = build_customer_pool(config.customer_pool_size)

    hub_name = os.environ.get("EVENT_HUB_NAME")
    label = (
        f"{limit:,}"
        if limit else "infinite"
    )
    print(f"Streaming to '{hub_name}' - {label} records, {interval}s interval (Ctrl+C to stop).")

    sent = 0
    try:
        with _build_client() as client:
            while limit == 0 or sent < limit:
                ride_id = _send_one(client, config, driver_pool, customer_pool)
                sent += 1
                print(f"    [{sent}] Sent: {ride_id}")
                time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\nStopped. {sent:,} records sent.")


def run(args) -> None:
    """
    Execute the Event Hub mode based on CLI arguments.

    Args:
        args:   Parsed command-line interface (CLI) arguments containing:
                - mode
                - interval
                - count
                - debug
    """
    load_dotenv()
    config = RuntimeConfig(debug=args.debug)

    if args.mode == "single":
        _run_single(config)
    elif args.mode == "stream":
        _run_stream(config, interval=args.interval, limit=args.count)
