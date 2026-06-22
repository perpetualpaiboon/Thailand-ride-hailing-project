"""
Main entry point for the ride-hailing data generator.

Supports three modes:

    generate    Print ride records to the terminal.
    historical  Save ride records to a file.
    eventhub    Send ride records to Azure Event Hub.

Usage:
    # Print 5 ride records to the terminal
    python data_generator.py generate --count 5

    # Generate 25,000 records and save to a CSV file
    python data_generator.py historical --count 25000 --format csv --duration 2026-01-01:2026-02-01

    # Send one record to Azure Event Hub
    python data_generator.py eventhub --mode single

    # Stream records to Azure Event Hub continuously
    python data_generator.py eventhub --mode stream --interval 0.5
"""

import argparse

from generator.modes import generate, historical, eventhub


def _build_parser() -> argparse.ArgumentParser:
    """
    Set up and return the argument parser with all subcommands.
    Determines what commands can be typed in the terminal.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Generate simulated ride-hailing records.",
    )
    subparsers = parser.add_subparsers(
        dest    = "command",
        metavar = "MODE"
    )

    # --- generate ---
    # Prints ride records to the terminal. Useful for quick testing.
    parser_generate = subparsers.add_parser(
        "generate",
        help="Generate ride records and print them to the terminal.",
    )
    parser_generate.add_argument(
        "--count", type=int, default=1, metavar="N",
        help="Number of records to generate (default: 1).",
    )
    parser_generate.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Show extra logs during location generation.",
    )

    # --- historical ---
    # Saves ride records to a local file for later upload.
    parser_historical = subparsers.add_parser(
        "historical",
        help="Generate a batch of ride records and save them to a file.",
    )
    parser_historical.add_argument(
        "--count", type=int, default=1, metavar="N",
        help="Number of records to generate (default: 1).",
    )
    parser_historical.add_argument(
        "--format", choices=["json", "csv"],
        required=True,
        help="Output file format: json or csv.",
    )
    parser_historical.add_argument(
        "--duration",
        metavar="START:END",
        required=True,
        help="Date range for ride timestamps. Format: YYYY-MM-DD:YYYY-MM-DD (e.g. 2026-01-01:2026-02-01).",
    )
    parser_historical.add_argument(
        "--driver-pool",
        metavar="PATH",
        default=None,
        help="Path to a saved driver pool file. If not provided, a new one is created.",
    )
    parser_historical.add_argument(
        "--customer-pool",
        metavar="PATH",
        default=None,
        help="Path to a saved customer pool file. If not provided, a new one is created.",
    )

    # --- eventhub ---
    # Sends ride records to Azure Event Hub.
    parser_eventhub = subparsers.add_parser(
        "eventhub",
        help="Send ride records to Azure Event Hub.",
    )
    parser_eventhub.add_argument(
        "--mode", choices=["single", "stream"],
        required=True,
        help="single: send one record. stream: keep sending until stopped.",
    )
    parser_eventhub.add_argument(
        "--interval", type=float, default=1.0,
        help="Seconds to wait between each send in stream mode (default: 1.0).",
    )
    parser_eventhub.add_argument(
        "--count", type=int, default=0, metavar="N",
        help="How many records to send. 0 means run until Ctrl+C (default: 0).",
    )
    parser_eventhub.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Show extra logs during location generation.",
    )

    return parser


def main() -> None:
    """
    Read arguments from the command line and run the selected mode.
    """
    parser = _build_parser()
    args = parser.parse_args()

    # Match the subcommand name to its run function.
    _command_map = {
        "generate"  : generate.run,
        "historical": historical.run,
        "eventhub"  : eventhub.run,
    }
    _command_map[args.command](args)


if __name__ == "__main__":
    main()