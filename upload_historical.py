"""
Script to upload historical ride data files to Azure cloud storage.

Looks for CSV and JSON files in the local 'data/historical_data/' folder
and uploads them to Azure Data Lake Storage Gen2 (ADLS).

Credentials are loaded from environment variables or a '.env' file.

Required environment variables:
    AZURE_STORAGE_CONNECTION_STRING:    Connection string for the Azure storage account.
    STORAGE_ACCOUNT_CONTAINER_NAME:     Name of the target storage container.

Usage:
    # Upload all files
    python upload_historical.py

    # Upload specific files by name
    python upload_historical.py --files historical_20260101_20260201.csv historical_20260201_20260301.csv

    # Upload files whose start date falls within a date range (inclusive)
    python upload_historical.py --from-date 20260101 --to-date 20260401
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

from azure.storage.blob import BlobServiceClient

from settings.storage import (
    AZURE_STORAGE_CONNECTION_STRING,
    ADLS_CONTAINER_NAME,
    ADLS_HISTORICAL_PREFIX,
    HISTORICAL_DATA_DIR,
)

# Pattern used to extract dates from filenames like: historical_20260101_20260201.csv
_FILENAME_PATTERN = re.compile(r"^historical_(\d{8})_(\d{8})\.(csv|json)$")
_DATE_FMT         = "%Y%m%d"


# --- Client ---

def _build_client() -> BlobServiceClient:
    """
    Create a connection to Azure storage using the credentials in the environment.

    Raises:
        EnvironmentError: If AZURE_STORAGE_CONNECTION_STRING is not set.
    """
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise EnvironmentError(
            "Missing required environment variable.\n"
            "Ensure AZURE_STORAGE_CONNECTION_STRING is set in your .env file."
        )
    return BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


# --- File selection ---


def _all_local_files() -> list[Path]:
    """
    Return all CSV and JSON files found in the historical data folder.

    Returns:
        list[Path]: A list of file paths found in HISTORICAL_DATA_DIR.
    """
    return [
        f
        for f in HISTORICAL_DATA_DIR.iterdir()
        if f.suffix in (".csv", ".json")
    ]


def _select_by_names(names: list[str]) -> list[Path]:
    """
    Return the file paths for a given list of filenames.

    Args:
        names (list[str]): List of filenames to look up.

    Returns:
        list[Path]: File paths that were found locally.
    """
    selected = []
    for name in names:
        path = HISTORICAL_DATA_DIR / name
        if path.exists():
            selected.append(path)
        else:
            print(f"  [WARNING] File not found locally, skipping: {name}")
    return selected


def _select_by_date_range(from_date: datetime, to_date: datetime) -> list[Path]:
    """
    Return files whose start date falls within the given date range (inclusive).

    The start date is read from the filename, which must follow the format:
        historical_YYYYMMDD_YYYYMMDD.csv / .json

    Args:
        from_date (datetime):   Start of the date range.
        to_date (datetime):     End of the date range.

    Returns:
        list[Path]: Matching files sorted by filename.
    """
    selected = []
    for f in _all_local_files():
        match = _FILENAME_PATTERN.match(f.name)

        # Skip files that do not follow the expected naming format.
        if not match:
            print(f"  [WARNING] Filename does not match expected pattern, skipping: {f.name}")
            continue

        # Compare the start date written in the filename against the given range.
        file_start = datetime.strptime(match.group(1), _DATE_FMT)
        if from_date <= file_start <= to_date:
            selected.append(f)

    return sorted(selected)


# --- Upload ---

def _upload(files: list[Path]) -> None:
    """
    Upload a list of local files to Azure cloud storage.

    Each file is placed under the historical data folder in the storage
    container. Existing files with the same name are overwritten.

    Args:
        files (list[Path]): List of local file paths to upload.
    """
    if not files:
        print("No files matched the selection criteria.")
        return

    client    = _build_client()
    container = client.get_container_client(ADLS_CONTAINER_NAME)

    print(f"Uploading {len(files)} file(s) to {ADLS_CONTAINER_NAME}/{ADLS_HISTORICAL_PREFIX}/")

    for file in files:
        # Build the full path inside the storage container.
        blob_name = f"{ADLS_HISTORICAL_PREFIX}/{file.name}"
        with open(file, "rb") as data:
            container.upload_blob(name=blob_name, data=data, overwrite=True)
        print(f"  Uploaded: {file.name}")

    print("Done.")


# --- CLI ---

def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments and return the result.

    Returns:
        argparse.Namespace: Parsed arguments from the command line.
    """
    parser = argparse.ArgumentParser(
        description="Upload historical ride data files to Azure cloud storage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload all files:
    python upload_historical.py

  Upload specific files:
    python upload_historical.py --files historical_20260101_20260201.csv

  Upload files within a date range:
    python upload_historical.py --from-date 20260101 --to-date 20260401
        """,
    )

    parser.add_argument(
        "--files",
        nargs  = "+",
        metavar= "FILENAME",
        help   = "One or more specific filenames to upload (e.g. historical_20260101_20260201.csv).",
    )
    parser.add_argument(
        "--from-date",
        metavar = "YYYYMMDD",
        help    = "Start of the date range filter (inclusive). Requires --to-date.",
    )
    parser.add_argument(
        "--to-date",
        metavar = "YYYYMMDD",
        help    = "End of the date range filter (inclusive). Requires --from-date.",
    )

    args = parser.parse_args()

    # Both --from-date and --to-date must be provided together.
    if bool(args.from_date) ^ bool(args.to_date):
        parser.error("--from-date and --to-date must be used together.")

    return args


def run() -> None:
    """
    Reads arguments from the command line, selects the matching files,
    and uploads them to Azure cloud storage.
    """
    args = _parse_args()

    all_files = _all_local_files()
    if not all_files:
        print(f"No historical data files found in {HISTORICAL_DATA_DIR}.")
        return

    # --- Determine which files to upload ---

    if args.files:
        # Upload only the files specified by name.
        files = _select_by_names(args.files)

    elif args.from_date and args.to_date:
        # Upload files whose start date falls within the given range.
        try:
            from_dt = datetime.strptime(args.from_date, _DATE_FMT)
            to_dt   = datetime.strptime(args.to_date,   _DATE_FMT)
        except ValueError:
            raise ValueError("Dates must be in YYYYMMDD format (e.g. 20260101).")

        if from_dt > to_dt:
            raise ValueError("--from-date must be earlier than --to-date.")

        files = _select_by_date_range(from_dt, to_dt)

    else:
        # If no extra arguments were provided, upload everything.
        files = sorted(all_files)

    _upload(files)


if __name__ == "__main__":
    run()
