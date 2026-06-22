"""
Configuration for the ride data generator.

This module contains runtime settings, probability distributions, and 
parameters used to shape generated ride records, including location selection,
trip distance, ride option suitability, pricing behavior, and ratings.
"""

from dataclasses import dataclass
from datetime import datetime


# --- Runtime Settings ---

@dataclass
class RuntimeConfig:
    """
    Configuration for the data generation session.

    Attributes:
        debug (bool):                   Enable logging for the Nominatim geocoder.
        completed_rate (float):         Target ratio of completed rides to cancelled rides (0.0 to 1.0).
        hot_province_chance (float):    Probability of selecting a popular province.
        num_records (int):              Number of ride records to generate per run.
        start_date (datetime | None):   Start of the date range for generated timestamps. Used in historical mode.
        end_date (datetime | None):     End of the date range for generated timestamps. Used in historical mode.
        driver_pool_size (int):         The total number of unique drivers to create.
        customer_pool_size (int):       The total number of unique customers to create.
    """
    debug: bool = True
    completed_rate: float = 0.80
    hot_province_chance: float = 0.80
    num_records: int = 1
    start_date: datetime | None = None
    end_date: datetime | None = None
    driver_pool_size: int = 500  
    customer_pool_size: int = 5000    


DEFAULT_CONFIG = RuntimeConfig()


# --- Province Selection Configuration  ---

# Set of popular province IDs that serve as hotspots for generated pickup and dropoff locations.
HOT_PROVINCE_IDS = {
    "TH-10",  # Bangkok
    "TH-20",  # Chon Buri (Pattaya)
    "TH-83",  # Phuket
    "TH-50",  # Chiang Mai
    "TH-90",  # Songkhla (Hat Yai)
    "TH-40",  # Khon Kaen
    "TH-77",  # Prachuap Khiri Khan (Hua Hin)
    "TH-30",  # Nakhon Ratchasima
    "TH-41",  # Udon Thani
    "TH-84",  # Surat Thani
    "TH-12",  # Nonthaburi
}

# Probability (0.0 to 1.0) that a ride's dropoff is located in the same province as its pickup.
SAME_PROVINCE_DROPOFF_CHANCE = 0.70

# Probability (0.0 to 1.0) that a cross-province ride is routed to one of the designated popular provinces.
# This only applies if the ride does not drop off in the pickup province.
HOT_PROVINCE_DROPOFF_CHANCE = 0.60


# --- Distance Configuration ---

# Probability distribution for generating trip distances.
# Weights determine generation frequency and are relative (they do not need to sum to 1).
TRIP_DISTANCE_CATEGORIES = [
    {"name": "medium",      "min_km": 0,    "max_km": 15,           "weight": 0.600},
    {"name": "long",        "min_km": 15,   "max_km": 30,           "weight": 0.250},
    {"name": "very_long",   "min_km": 30,   "max_km": 100,          "weight": 0.120},
    {"name": "ultra_long",  "min_km": 100,  "max_km": 300,          "weight": 0.025},
    {"name": "extreme",     "min_km": 300,  "max_km": 600,          "weight": 0.004},
    {"name": "outlier",     "min_km": 600,  "max_km": float("inf"), "weight": 0.001},
]

# Distance tiers used to classify trips for ride option suitability.
DISTANCE_TIERS = [
    {"name": "city_short",    "max_km": 5.0},
    {"name": "city_medium",   "max_km": 15.0},
    {"name": "suburban",      "max_km": 80.0},
    {"name": "regional",      "max_km": 250.0},
    {"name": "cross_country", "max_km": float("inf")},
]

# Multiplier applied to the raw geodesic (straight-line) distance to approximate actual road travel distance.
ROAD_DISTANCE_FACTOR = 1.5


# --- Speed Configuration ---

# Speed ranges (km/h) used to estimate travel duration based on trip distance.
SPEED_TIERS = [
    {"max_km": 5.0,          "min_speed": 15.0, "max_speed": 25.0},
    {"max_km": 20.0,         "min_speed": 30.0, "max_speed": 45.0},
    {"max_km": 80.0,         "min_speed": 55.0, "max_speed": 75.0},
    {"max_km": float("inf"), "min_speed": 80.0, "max_speed": 105.0},
]

# Random variation applied to generated speeds to simulate traffic and real-world road conditions.
SPEED_NOISE_RANGE = (0.85, 1.15)


# --- Ride Option Selection Configuration ---

#  min_passengers_ratio (float):    Determines the minimum passenger count generated,
#                                   expressed as a proportion of the vehicle's maximum capacity
#                                   (e.g., 0.5 means 50% full).
#                                   It is always floored to 1 so a ride never has 0 passengers.

#  distance_weights (dict):         Relative selection weights mapped to DISTANCE_TIERS names.
#                                   A weight of 0 means the vehicle is not suitable for that tier.
#                                   (e.g., Bikes have a weight of 0 for suburban or higher tiers).

# To add a new ride option, add its ID and configuration here.
RIDE_OPTION_CONFIG = {
    1: {  # Economy
        "min_passengers_ratio": 0.0,
        "distance_weights":
            {
                "city_short": 30,
                "city_medium": 60,
                "suburban": 50,
                "regional": 0,
                "cross_country": 0,
            },
    },
    2: {  # Taxi
        "min_passengers_ratio": 0.0,
        "distance_weights":
            {
                "city_short": 30,
                "city_medium": 60,
                "suburban": 50,
                "regional": 0,
                "cross_country": 0,
            },
    },
    3: {  # Bike (Capacity: 1. Ratio of 1.0 guarantees exactly 1 passenger)
        "min_passengers_ratio": 1.0,
        "distance_weights":
            {
                "city_short": 70,
                "city_medium": 60,
                "suburban": 0,
                "regional": 0,
                "cross_country": 0,
            },
    },
    4: {  # Premium
        "min_passengers_ratio": 0.0,
        "distance_weights":
            {
                "city_short": 0,
                "city_medium": 10,
                "suburban": 30,
                "regional": 30,
                "cross_country": 0,
            },
    },
    5: {  # SUV (Requires at least half capacity, e.g., 2+ passengers)
        "min_passengers_ratio": 0.5,
        "distance_weights":
            {
                "city_short": 0,
                "city_medium": 10,
                "suburban": 30,
                "regional": 30,
                "cross_country": 10,
            },
    },
    6: {  # Van (Requires at least half capacity, e.g., 5+ passengers)
        "min_passengers_ratio": 0.5,
        "distance_weights": {
            "city_short": 0,
            "city_medium": 0,
            "suburban": 5,
            "regional": 70,
            "cross_country": 90,
        },
    },
}


# --- Surge Pricing Configuration ---

# Surge period defined as (start_hour, end_hour) in 24-hour time.
SURGE_HOURS = (
    (7, 9),    # 7 AM to 9 AM
    (17, 20),  # 5 PM to 8 PM
)

# Bounds for the surge multiplier applied during active surge hours.
SURGE_MULTIPLIER_RANGE = (1.2, 1.5)


# --- Tipping Configuration ---

# Probability (0.0 to 1.0) that a passenger includes a tip.
TIP_CHANCE = 0.20

# Bounds for the tip amount, calculated as a randomized percentage of the subtotal.
TIP_RATE_RANGE = (0.05, 0.20)


# --- Driver Rating & Rides Ratings ---

# Bounds for generating a driver's average rating.
DRIVER_RATING_RANGE = (3.5, 5.0)

# Maximum +/- rating deviation applied to a driver's rating
# for a passenger's single-ride rating.
RATING_NOISE = 1.5


# --- Trip Timestamp ---

# Maximum historical age limit (days and hours)
# subtracted from the reference time to generate a trip timestamp.
MAX_TRIP_AGE_DAYS = 0
MAX_TRIP_AGE_HOURS = 23

