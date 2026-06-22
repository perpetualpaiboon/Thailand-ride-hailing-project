"""
This module is a place for all folder paths and Azure storage settings.

Any script that reads or writes local data files, or uploads to Azure,
should import its paths from here.

Required environment variables:
    AZURE_STORAGE_CONNECTION_STRING:    Connection string for the Azure storage account.
    STORAGE_ACCOUNT_CONTAINER_NAME:     Name of the target storage container.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Local Paths ---

# Root of the local data directory (repo_root/data/)
DATA_DIR = Path(__file__).parent.parent / "data"

HISTORICAL_DATA_DIR = DATA_DIR / "historical_data"
MAPPING_DATA_DIR    = DATA_DIR / "mapping_data"


# --- ADLS Layout ---

ADLS_CONTAINER_NAME     = os.environ.get("STORAGE_ACCOUNT_CONTAINER_NAME")
ADLS_HISTORICAL_PREFIX  = "bronze/manual_uploads/historical_data"
ADLS_MAPPING_PREFIX     = "bronze/mapping_data"


# --- Azure Credentials ---

AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
