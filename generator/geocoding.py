"""
Geocoding utility functions powered by a local Nominatim Docker instance.

This module provides functions to generate valid, randomized geographic 
coordinates within specific Thai provinces, perform land validation via 
reverse geocoding, and automatically retry on failures.
"""

import json
import random
import time

from geopy.geocoders import Nominatim

from generator.config import DEFAULT_CONFIG, RuntimeConfig


# --- Nominatim Client ---

geolocator = Nominatim(
    domain="localhost:8080",
    scheme="http",
    user_agent="ride_hailing_pipeline_project",
)


# --- Address Validation ---

# Set of address keys returned by Nominatim reverse geocoding.
_ADDRESS_KEYS = {
    "continent", "country", "country_code",

    "region", "state", "state_district", "county", "ISO3166-2-lvl4", "ISO3166-2-lvl6",

    "municipality", "city", "town", "village",
    "city_district", "district", "borough", "suburb", "subdivision",
    "hamlet", "croft", "isolated_dwelling",

    "neighbourhood", "allotments", "quarter",
    "city_block", "residential", "farm", "farmyard", "industrial", "commercial", "retail",

    "road", "house_number", "house_name",

    "emergency", "historic", "military", "natural", "landuse", "place", "railway",
    "man_made", "aerialway", "boundary", "amenity", "aeroway", "club", "craft",
    "leisure", "office", "mountain_pass", "shop", "tourism", "bridge", "tunnel", "waterway",

    "postcode"
}

# Address keys that Nominatim returns even for ocean/sea coordinates.
# These keys alone are not sufficient to confirm that a coordinate is on land.
_COMMON_KEYS = {
    "country", "country_code", "city", "continent",
    "region", "state", "province", "ISO3166-2-lvl4", "ISO3166-2-lvl6",
}

# Specific local keys derived by excluding common keys.
# The presence of any of these keys strongly suggests the coordinate is on land.
_SPECIFIC_LOCAL_KEYS = _ADDRESS_KEYS - _COMMON_KEYS


def is_valid_land(address: dict) -> bool:
    """
    Check whether a reverse-geocoded address dictionary represents a land location.

    Nominatim may return generic keys (like 'country' or 'region') even when 
    coordinates point to the ocean. A valid land location is expected to contain 
    at least one more specific address field (e.g., 'road', 'suburb', 'postcode').

    Args:
        address (dict): The raw address dictionary returned by Nominatim.

    Returns:
        bool: True if the address contains land-specific keys, False otherwise.
    """
    return any(key in _SPECIFIC_LOCAL_KEYS for key in address)


# --- Location Generation ---

MAX_RETRIES = 500
def generate_location(province: dict, config: RuntimeConfig = DEFAULT_CONFIG):
    """
    Generates a random valid geographic coordinate within a specified province.

    The function:
    1. Retrieves the province bounding box from Nominatim.
    2. Randomly samples a latitude and longitude within that bounding box.
    3. Reverse-geocodes the coordinate to verify that:
        - the location is on land,
        - the coordinate is within Thailand,
        - and the province matches the requested province ID.

    Retries automatically on each failed attempt up to MAX_RETRIES times.
    Raises RuntimeError if no valid coordinate is found within the limit.

    Args:
        province (dict): A province dictionary containing 'province_name' and 'province_id'.
        config (RuntimeConfig): Runtime configuration used for controlling debug logging.

    Returns:
        tuple[float, float, str]: A tuple containing (latitude, longitude, address).

    Raises:
        RuntimeError: If a valid coordinate could not be found after MAX_RETRIES attempts.
    """
    province_name = province["province_name"]
    attempt = 0

    while attempt < MAX_RETRIES:
        try:
            location = geolocator.geocode(f"{province_name}, Thailand")
            bbox = location.raw["boundingbox"]
            min_latitude, max_latitude = float(bbox[0]), float(bbox[1])
            min_longitude, max_longitude = float(bbox[2]), float(bbox[3])

            latitude = random.uniform(min_latitude, max_latitude)
            longitude = random.uniform(min_longitude, max_longitude)

            if config.debug:
                print(
                    f"Bounds: ({min_latitude}, {min_longitude}) -> ({max_latitude}, {max_longitude})\n"
                    f"Sampled: ({latitude}, {longitude})"
                )

            reverse = geolocator.reverse((latitude, longitude))
            if reverse is None:
                if config.debug:
                    print("---Retry: no address returned---")
                attempt += 1
                continue

            address = reverse.raw["address"]

            if config.debug:
                print(json.dumps(address, indent=2, ensure_ascii=False))

            if not is_valid_land(address):
                if config.debug:
                    print("---Retry: point is not on land---")
                attempt += 1
                continue

            if address.get("country_code") != "th":
                if config.debug:
                    print("---Retry: outside Thailand---")
                attempt += 1
                continue

            province_code = address.get("ISO3166-2-lvl4")
            if config.debug:
                print(
                    f"Province code: {province_code} | Expected: {province['province_id']}")

            if province_code != province["province_id"]:
                if config.debug:
                    print("---Retry: wrong province---")
                attempt += 1
                continue

            return latitude, longitude, reverse.address

        except Exception as e:
            attempt += 1
            print(f"Geocoding error (attempt {attempt}): {e}.")
            time.sleep(1)

    raise RuntimeError(
        f"Could not find a valid coordinate in {province_name} after {MAX_RETRIES} attempts. "
    )
