"""
Loads all dimension tables from the Data/ directory as module-level constants.

This module loads commonly used data into constants 
and merges generator configurations (e.g. vehicle distance weights and passenger ratios) 
into ride option records so all related configuration
can be accessed from a single source.
"""

import json

from settings.storage import MAPPING_DATA_DIR
from generator.config import HOT_PROVINCE_IDS, RIDE_OPTION_CONFIG


# --- Data Mapping Loading ---

def load_mapping(filename: str) -> list[dict]:
    """
    Reads a JSON file from the Data/ directory and returns its contents as a list.

    Args:
        filename (str): File name without the .json extension (e.g. 'map_provinces').

    """
    path = MAPPING_DATA_DIR / f"{filename}.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# --- Dimension Tables ---

PROVINCES            = load_mapping("map_provinces")
RIDE_STATUSES        = load_mapping("map_ride_statuses")
CANCELLATION_REASONS = load_mapping("map_cancellation_reasons")

# Only load active payment methods - retired ones should not be assigned to new rides.
PAYMENT_METHODS = [
    p for p in load_mapping("map_payment_methods")
    if p.get("is_active", True)
]

# Only load active ride options - retired ones should not be assigned to new rides.
RIDE_OPTIONS = [
    o for o in load_mapping("map_ride_options")
    if o.get("is_active", True)
]

# Merge min_passengers_ratio (for calculating minimum passenger counts)
# and distance_weights (for vehicle suitability based on trip length) into each RIDE_OPTIONS element.
# This ensures all ride option data can be accessed through a single constant.
for _option in RIDE_OPTIONS:
    _option.update(RIDE_OPTION_CONFIG.get(_option["ride_option_id"], {}))


# --- Constants ---

# Set of designated popular provinces (e.g., Bangkok)
HOT_PROVINCES = [
    p
    for p in PROVINCES
    if p["province_id"] in HOT_PROVINCE_IDS
]

# Set of provinces (excluding popular provinces)
OTHER_PROVINCES = [
    p
    for p in PROVINCES
    if p["province_id"] not in HOT_PROVINCE_IDS
]

# List of actual cancellation reasons
VALID_CANCEL_REASONS = [
    r
    for r in CANCELLATION_REASONS
    if r["initiator"] is not None
]

# Constant representing completed trips with no cancellation
NO_CANCEL_REASON_ID = next(
    r["cancellation_reason_id"]
    for r in CANCELLATION_REASONS
    if r["initiator"] is None
)

# Constant representing the ride_status_id for a completed ride.
COMPLETED_STATUS_ID = next(
    s["ride_status_id"]
    for s in RIDE_STATUSES
    if s["ride_status"] == "Completed"
)

# Constant representing the ride_status_id for a cancelled ride.
CANCELLED_STATUS_ID = next(
    s["ride_status_id"]
    for s in RIDE_STATUSES
    if s["ride_status"] == "Cancelled"
)
