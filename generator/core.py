"""
Ride record generation module.

This module handles the simulation: province selection, vehicle assignment, 
fare calculation, and ride record generation. 

The entry point is generate_ride_record(). All other functions in 
this module are supporting functions for the simulation workflow.
"""

import math
import random
import uuid
from datetime import datetime, timedelta
from typing import NamedTuple

import ulid
from faker import Faker
from geopy.distance import geodesic

from generator.config import (
    DEFAULT_CONFIG,
    DISTANCE_TIERS,
    DRIVER_RATING_RANGE,
    HOT_PROVINCE_DROPOFF_CHANCE,
    MAX_TRIP_AGE_DAYS,
    MAX_TRIP_AGE_HOURS,
    RATING_NOISE,
    ROAD_DISTANCE_FACTOR,
    SAME_PROVINCE_DROPOFF_CHANCE,
    SPEED_NOISE_RANGE,
    SPEED_TIERS,
    SURGE_HOURS,
    SURGE_MULTIPLIER_RANGE,
    TIP_CHANCE,
    TIP_RATE_RANGE,
    TRIP_DISTANCE_CATEGORIES,
    RuntimeConfig,
)
from generator.geocoding import generate_location
from generator.pool import Customer, Driver, generate_license_plate
from generator.loader import (
    CANCELLED_STATUS_ID,
    COMPLETED_STATUS_ID,
    HOT_PROVINCES,
    NO_CANCEL_REASON_ID,
    OTHER_PROVINCES,
    PAYMENT_METHODS,
    PROVINCES,
    RIDE_OPTIONS,
    VALID_CANCEL_REASONS,
)

fake = Faker("th_TH")


# --- Data Structures ---

class TripLocations(NamedTuple):
    """Geocoded pickup and dropoff coordinates for a single trip."""
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    dropoff_province: dict
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: str
    travel_distance_km: float


# --- Province Selection ---

def select_pickup_province(config: RuntimeConfig = DEFAULT_CONFIG) -> dict:
    """
    Randomly selects a pickup province with a higher probability for designated popular provinces.

    Uses the 'hot_province_chance' from the provided configuration defined in 
    config.py to determine whether to randomly select from the HOT_PROVINCES 
    or the OTHER_PROVINCES pool.

    Args:
        config (RuntimeConfig): Configuration containing the 'hot_province_chance' probability.

    Returns:
        dict: The randomly selected province dictionary.
    """
    pool = (
        HOT_PROVINCES
        if random.random() < config.hot_province_chance
        else OTHER_PROVINCES
    )
    return random.choice(pool)


def _select_dropoff_province(pickup_province: dict) -> dict:
    """
    Selects a random dropoff province using a weighted probability distribution.

    The selection follows these probabilities:
        - SAME_PROVINCE_DROPOFF_CHANCE chance                                           : The same province as the pickup location.
        - (1 - SAME_PROVINCE_DROPOFF_CHANCE) * HOT_PROVINCE_DROPOFF_CHANCE chance       : A randomly selected popular province.
        - (1 - SAME_PROVINCE_DROPOFF_CHANCE) * (1 - HOT_PROVINCE_DROPOFF_CHANCE) chance : Any random province.

    Args:
        pickup_province (dict): The pickup province dictionary.

    Returns:
        dict: The selected dropoff province dictionary.
    """
    if random.random() < SAME_PROVINCE_DROPOFF_CHANCE:
        return pickup_province
    if random.random() < HOT_PROVINCE_DROPOFF_CHANCE:
        return random.choice(HOT_PROVINCES)
    return random.choice(PROVINCES)


# --- Distance & Location ---

def select_distance_category() -> dict:
    """
    Selects a random trip distance category based on probability weights.

    The selection is weighted according to the 'weight' value specified 
    in each category within the TRIP_DISTANCE_CATEGORIES defined in config.py.

    Returns:
        dict: The randomly selected distance category dictionary.
    """
    weights = [
        c["weight"]
        for c in TRIP_DISTANCE_CATEGORIES
    ]
    return random.choices(TRIP_DISTANCE_CATEGORIES, weights=weights, k=1)[0]


def select_trip_locations(
        pickup_province: dict,
        distance_category: dict,
        config: RuntimeConfig = DEFAULT_CONFIG
) -> TripLocations:
    """
    Generates valid pickup and dropoff locations that satisfy a specific distance category.

    The pickup location is generated once. The dropoff location and province are repeatedly regenerated
    until the estimated travel distance falls within the category's minimum and maximum distance range.

    Args:
        pickup_province (dict):     The pickup province dictionary.
        distance_category (dict):   A dictionary containing the minimum and maximum distance range ('min_km' and 'max_km').
        config (RuntimeConfig):     Runtime configuration used for controlling debug logging.

    Returns:
        TripLocations:  A tuple containing generated coordinates, addresses, selected dropoff province,
                        and the travel distance.
    """
    pickup_latitude, pickup_longitude, pickup_address = generate_location(
        pickup_province, config)
    attempt = 0

    while True:
        attempt += 1
        if config.debug:
            print(f"select_trip_locations attempt: {attempt}")

        dropoff_province = _select_dropoff_province(pickup_province)
        dropoff_latitude, dropoff_longitude, dropoff_address = generate_location(
            dropoff_province, config)

        # Calculate the geodesic (straight-line) distance between the two coordinates.
        straight_km = geodesic(
            (pickup_latitude, pickup_longitude), (dropoff_latitude, dropoff_longitude)
        ).kilometers

        travel_distance_km = straight_km * ROAD_DISTANCE_FACTOR

        if config.debug:
            print(f"Distance: {travel_distance_km:.2f} km")

        if distance_category["min_km"] <= travel_distance_km <= distance_category["max_km"]:
            return TripLocations(
                pickup_latitude, pickup_longitude, pickup_address,
                dropoff_province, dropoff_latitude, dropoff_longitude, dropoff_address,
                travel_distance_km,
            )


def _get_distance_tier_name(travel_distance_km: float) -> str:
    """
    Maps a travel distance to its corresponding tier name.

    Iterates through the DISTANCE_TIERS configuration to check the distance tiers 
    in order and return the first matching distance tier name. If the distance 
    exceeds all defined limits, it defaults to the highest tier.

    Args:
        travel_distance_km (float): The travel distance in kilometers.

    Returns:
        str: The corresponding distance tier name (e.g., 'city_short', 'suburban').
    """
    for tier in DISTANCE_TIERS:
        if travel_distance_km <= tier["max_km"]:
            return tier["name"]
    return DISTANCE_TIERS[-1]["name"]


# --- Ride Option (Vehicle) Selection ---

def select_ride_option(travel_distance_km: float) -> dict:
    """
    Picks a ride option weighted by how suitable it is for the trip distance.

    This function first determines the matching distance tier, then
    applies the 'distance_weights' in RIDE_OPTIONS for each ride option.
    A weight of 0 prevents a ride option from being selected for that distance range.

    Args:
        travel_distance_km (float): The travel distance in kilometers.

    Returns:
        dict: The randomly selected ride option dictionary.
    """
    tier = _get_distance_tier_name(travel_distance_km)
    weights = [
        option.get("distance_weights", {}).get(tier, 0)
        for option in RIDE_OPTIONS
    ]
    return random.choices(RIDE_OPTIONS, weights=weights, k=1)[0]


def generate_passenger_count(ride_option: dict) -> int:
    """
    Generates a random passenger count for the selected ride option.

    To simulate realistic ride records, this function calculates a minimum passenger count 
    using the 'min_passengers_ratio' to prevent large vehicles from appearing nearly empty.

    Args:
        ride_option (dict): The selected ride option dictionary containing 'min_passengers_ratio'.

    Returns:
        int: A random passenger count between the calculated minimum and the vehicle's maximum capacity.
    """
    capacity = ride_option["passenger_capacity"]
    min_ratio = ride_option.get("min_passengers_ratio", 0.0)
    min_count = max(1, math.ceil(capacity * min_ratio))
    return random.randint(min_count, capacity)


# --- Finance Generation---

def _is_surge_hour(hour: int) -> bool:
    """
    Check if a given hour falls within any configured surge period.

    Args:
        hour (int): The hour of the day (0-23) to check.

    Returns:
        bool: True if the hour is within a surge period, False otherwise.
    """
    return any(start <= hour <= end for start, end in SURGE_HOURS)


def calculate_surge_multiplier(pickup_time: datetime) -> float:
    """
    Generates a surge multiplier based on the pickup time.

    During configured surge periods (e.g., morning and evening rush hours), 
    the multiplier is randomly generated within the SURGE_MULTIPLIER_RANGE defined in config.py. 
    Outside surge periods, the function returns the default multiplier of 1.0.

    Args:
        pickup_time (datetime): The pickup date and time.

    Returns:
        float: The generated surge multiplier, rounded to two decimal places.
    """
    if _is_surge_hour(pickup_time.hour):
        return round(random.uniform(*SURGE_MULTIPLIER_RANGE), 2)
    return 1.0


def calculate_finance(
        pickup_time: datetime,
        travel_distance_km: float,
        duration_minutes: int,
        ride_option: dict
) -> dict:
    """
    Generates all fare components for a completed trip.

    This function calculates the base, distance, and time fares, 
    then applies a surge multiplier based on the pickup time. 
    A randomized tip is optionally added using the TIP_CHANCE and TIP_RATE_RANGE defined in config.py.

    Args:
        pickup_time (datetime):     The pickup date and time.
        travel_distance_km (float): The travel distance in kilometers.
        duration_minutes (int):     The travel duration in minutes.

        ride_option (dict):     The selected ride option dictionary containing 
                                rate configurations ('base_rate', 'per_km', 'per_minute').

    Returns:
        dict:   A dictionary containing the full fare breakdown with the following keys:
                - base_fare
                - distance_fare
                - time_fare
                - surge_multiplier
                - subtotal
                - tip_amount
                - total_fare
    """
    base_fare = ride_option["base_rate"]
    distance_fare = round(travel_distance_km * ride_option["per_km"], 2)
    time_fare = round(duration_minutes * ride_option["per_minute"], 2)
    surge = calculate_surge_multiplier(pickup_time)
    subtotal = round((base_fare + distance_fare + time_fare) * surge, 2)
    tip_amount = round(subtotal * random.uniform(*TIP_RATE_RANGE)
                       ) if random.random() < TIP_CHANCE else 0.0
    total_fare = subtotal + tip_amount

    return {
        "base_fare":        base_fare,
        "distance_fare":    distance_fare,
        "time_fare":        time_fare,
        "surge_multiplier": surge,
        "subtotal":         subtotal,
        "tip_amount":       tip_amount,
        "total_fare":       total_fare,
    }


# --- Travel Time & Ratings Generation ---

def generate_travel_time(travel_distance_km: float) -> int:
    """
    Generates travel time in minutes for a given distance.

    Selects a speed range based on the distance thresholds in SPEED_TIERS, 
    applies random noise to simulate traffic conditions using SPEED_NOISE_RANGE 
    (both defined in config.py), and calculates the total duration rounded up 
    to the nearest minute.

    Args:
        travel_distance_km (float): The travel distance in kilometers.

    Returns:
        int: The travel duration in minutes.
    """
    tier = next(
        t
        for t in SPEED_TIERS
        if travel_distance_km <= t["max_km"]
    )
    base_speed = random.uniform(tier["min_speed"], tier["max_speed"])
    actual_speed = base_speed * random.uniform(*SPEED_NOISE_RANGE)
    return math.ceil((travel_distance_km / actual_speed) * 60)


def generate_ride_rating(driver_rating: float) -> int:
    """
    Simulates a passenger ride rating (1-5) influenced by the driver's average rating score.

    This function also add random variance using the RATING_NOISE defined in config.py 
    to ensure realistic feedback.

    Args:
        driver_rating (float): The driver's average rating.

    Returns:
        int: The generated ride rating (1-5).
    """
    return max(1, min(5, int(driver_rating + random.uniform(-RATING_NOISE, RATING_NOISE))))


# --- Ride Record Generation ---

def _build_cancelled_fields() -> dict:
    """
    Constructs the data fields for a cancelled trip.

    Sets distances and fares to zero, and timestamps and driver details to None. 
    Randomly selects a reason from the VALID_CANCEL_REASONS defined in config.py.

    Returns:
        dict: A dictionary containing data for a cancelled ride.
    """
    return {
        "cancellation_reason_id": random.choice(VALID_CANCEL_REASONS)["cancellation_reason_id"],
        "travel_distance_km":     0.0,
        "duration_minutes":       0,
        "passenger_count":        0,
        "pickup_timestamp":       None,
        "dropoff_timestamp":      None,
        "driver_rating":          None,
        "rating":                 None,
        "base_fare":              0.00,
        "distance_fare":          0.00,
        "time_fare":              0.00,
        "surge_multiplier":       1.0,
        "subtotal":               0.00,
        "tip_amount":             0.00,
        "total_fare":             0.00,
    }


def _build_completed_fields(
    reference_time: datetime,
    travel_distance_km: float,
    ride_option: dict,
) -> dict:
    """
    Constructs the data fields for a completed trip.

    Generates the trip duration, passenger count, timestamps, and a driver rating 
    using the DRIVER_RATING_RANGE defined in config.py, alongside all calculated 
    fare components.

    Args:
        reference_time (datetime):  The base time used to calculate timestamps.
        travel_distance_km (float): The travel distance in kilometers.
        ride_option (dict):         The selected ride option dictionary used to calculate fares.

    Returns:
        dict: A dictionary containing data for a completed ride.
    """
    duration_minutes = generate_travel_time(travel_distance_km)
    pickup_timestamp = reference_time
    dropoff_timestamp = reference_time + timedelta(minutes=duration_minutes)
    driver_rating = round(random.uniform(*DRIVER_RATING_RANGE), 1)
    finance = calculate_finance(
        pickup_timestamp, travel_distance_km, duration_minutes, ride_option
    )

    return {
        "cancellation_reason_id": NO_CANCEL_REASON_ID,
        "travel_distance_km":     travel_distance_km,
        "duration_minutes":       duration_minutes,
        "passenger_count":        generate_passenger_count(ride_option),
        "pickup_timestamp":       pickup_timestamp.isoformat(),
        "dropoff_timestamp":      dropoff_timestamp.isoformat(),
        "driver_rating":          driver_rating,
        "rating":                 generate_ride_rating(driver_rating),
        **finance,
    }


def generate_ride_record(
    config:        RuntimeConfig    = DEFAULT_CONFIG,
    driver_pool:   list[Driver]     | None = None,
    customer_pool: list[Customer]   | None = None,
) -> dict:
    """
    Generates a complete simulated ride record.

    This function coordinates the complete ride-generation workflow by:
    - determining whether the trip is completed or cancelled,
    - selecting trip distance and pickup province,
    - generating pickup and dropoff coordinates,
    - selecting ride options and payment methods,
    - sampling driver and customer from pre-built pools (if provided),
    - and constructing a single dictionary containing all the trip details.

    The resulting dataset can be used for testing, analytics simulations,
    seeding development databases, or generating synthetic ride-hailing data.

    Args:
        config (RuntimeConfig):         Runtime configuration controlling simulation behavior.
        driver_pool (list[Driver]):     Pre-built driver pool for reuse across rides.
                                        If None, a new random driver is generated per ride.
        customer_pool (list[Customer]): Pre-built customer pool for reuse across rides.
                                        If None, a new random customer is generated per ride.

    Returns:
        dict: A dictionary containing the complete simulated ride record.
    """
    is_cancelled = random.random() > config.completed_rate
    distance_category = select_distance_category()
    pickup_province = select_pickup_province(config)
    payment_method = random.choice(PAYMENT_METHODS)

    locations = select_trip_locations(
        pickup_province, distance_category, config)
    ride_option = select_ride_option(locations.travel_distance_km)

    if config.start_date and config.end_date:
        range_seconds = (config.end_date - config.start_date).total_seconds()
        reference_time = config.start_date + timedelta(seconds=random.uniform(0, range_seconds))
    else:
        reference_time = datetime.now() - timedelta(
            days=random.randint(0, MAX_TRIP_AGE_DAYS),
            hours=random.randint(0, MAX_TRIP_AGE_HOURS),
        )

    driver = (
        random.choice(driver_pool)
        if driver_pool
        else Driver(
            driver_id=             str(uuid.uuid4()),
            driver_name=           fake.name(),
            driver_phone=          fake.phone_number(),
            driver_license=        fake.bothify("########"),
            vehicle_id=            str(uuid.uuid4()),
            vehicle_license_plate= generate_license_plate(),
        )
    )

    customer = (
        random.choice(customer_pool)
        if customer_pool
        else Customer(
            booker_id=    str(uuid.uuid4()),
            booker_name=  fake.name(),
            booker_email= fake.email(),
            booker_phone= fake.phone_number(),
        )
    )

    ride_id = ulid.from_timestamp(reference_time).str
    ride_status_id = CANCELLED_STATUS_ID if is_cancelled else COMPLETED_STATUS_ID
    trip_fields = (
        _build_cancelled_fields()
        if is_cancelled
        else _build_completed_fields(reference_time, locations.travel_distance_km, ride_option)
    )

    return {
        "ride_id":               ride_id,
        "booker_id":             customer.booker_id,
        "driver_id":             driver.driver_id,
        "vehicle_id":            driver.vehicle_id,

        "ride_status_id":        ride_status_id,
        "pickup_city_id":        pickup_province["province_id"],
        "dropoff_city_id":       locations.dropoff_province["province_id"],
        "ride_option_id":        ride_option["ride_option_id"],
        "payment_method_id":     payment_method["payment_method_id"],

        "booking_timestamp":     reference_time.isoformat(),

        "pickup_latitude":       locations.pickup_latitude,
        "pickup_longitude":      locations.pickup_longitude,
        "pickup_address":        locations.pickup_address,
        "dropoff_latitude":      locations.dropoff_latitude,
        "dropoff_longitude":     locations.dropoff_longitude,
        "dropoff_address":       locations.dropoff_address,

        "booker_name":           customer.booker_name,
        "booker_email":          customer.booker_email,
        "booker_phone":          customer.booker_phone,
        "driver_name":           driver.driver_name,
        "driver_phone":          driver.driver_phone,
        "driver_license":        driver.driver_license,
        "vehicle_license_plate": driver.vehicle_license_plate,

        **trip_fields,
    }
