"""
Creates and loads lists of drivers and customers for the ride simulator.

This module creating a set of drivers and customers before the simulation starts,
we make sure the same people appear in multiple rides. This makes the final data
look more realistic when looking at how often people use the app.

Usage:
    from generator.pool import build_driver_pool, build_customer_pool

    driver_pool   = build_driver_pool(size=500)
    customer_pool = build_customer_pool(size=5000)

    # Pass both pools into generate_ride_record() for reuse across rides.
    record = generate_ride_record(config, driver_pool, customer_pool)

To reuse the same pools across multiple runs, use generate_pools.py to save
them to the files and load_driver_pool() / load_customer_pool() to reload them.
"""

import json
import random
import uuid
from dataclasses import dataclass
from pathlib import Path

from faker import Faker

# Setup the fake data generator for the Thai language
fake = Faker("th_TH")

# Thai letters used on vehicle license plates
_THAI_LETTERS = "กขคฆงจฉชซญฎฏฐทธนบปผพฟภมยรลวศษสหฬอฮ"


def generate_license_plate() -> str:
    """Generates a simulated Thai license plate.

    Returns:
        str: A random Thai license plate string.
    """
    letters = "".join(random.choices(_THAI_LETTERS, k=2))
    suffix_num = random.randint(1, 9999)
    if random.random() < 0.5:
        return f"{random.randint(1, 9)}{letters} {suffix_num}"
    return f"{letters} {suffix_num}"


@dataclass(frozen=True)
class Driver:
    """
    Holds information for a single driver.

    Attributes:
        driver_id (str):                A unique text ID for the driver.
        driver_name (str):              The driver's full name in Thai.
        driver_phone (str):             The driver's phone number.
        driver_license (str):           A random 8-digit license number.
        vehicle_id (str):               A unique text ID for the car.
        vehicle_license_plate (str):    The car's Thai license plate.
    """
    driver_id:             str
    driver_name:           str
    driver_phone:          str
    driver_license:        str
    vehicle_id:            str
    vehicle_license_plate: str


@dataclass(frozen=True)
class Customer:
    """
    Holds information for a single customer.

    Attributes:
        booker_id (str):    A unique text ID for the customer.
        booker_name (str):  The customer's full name in Thai.
        booker_email (str): The customer's email address.
        booker_phone (str): The customer's phone number.
    """
    booker_id:    str
    booker_name:  str
    booker_email: str
    booker_phone: str


def build_driver_pool(size: int) -> list[Driver]:
    """
    Creates a new list of drivers.

    Args:
        size (int): The number of drivers to create.

    Returns:
        list[Driver]: A list of newly created drivers.
    """
    pool = []
    for _ in range(size):
        pool.append(
            Driver(
                driver_id=             str(uuid.uuid4()),
                driver_name=           fake.name(),
                driver_phone=          fake.phone_number(),
                driver_license=        fake.bothify("########"),
                vehicle_id=            str(uuid.uuid4()),
                vehicle_license_plate= generate_license_plate(),
            )
        )
    return pool


def load_driver_pool(path: str | Path) -> list[Driver]:
    """
    Loads a saved list of drivers from a file.

    Args:
        path (str | Path):  Where the JSON file is located.

    Returns:
        list[Driver]:       The loaded list of drivers.

    Raises:
        FileNotFoundError:  If the file is missing. You need to run the setup script first.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Driver pool file not found: {path}\n"
            "Run generate_pools.py first to build the pool."
        )
    with path.open("r", encoding="utf-8") as f:
        pool = []
        for d in json.load(f):
            pool.append(Driver(**d))
        return pool

def build_customer_pool(size: int) -> list[Customer]:
    """
    Creates a new list of customers.

    Args:
        size (int):     The number of customers to create.

    Returns:
        list[Customer]: A list of newly created customers.
    """
    pool = []
    for _ in range(size):
        pool.append(
            Customer(
                booker_id=    str(uuid.uuid4()),
                booker_name=  fake.name(),
                booker_email= fake.email(),
                booker_phone= fake.phone_number(),
            )
        )
    return pool

def load_customer_pool(path: str | Path) -> list[Customer]:
    """
    Loads a saved list of customers from a file.

    Args:
        path (str | Path):  Where the JSON file is located.

    Returns:
        list[Customer]:     The loaded list of customers.

    Raises:
        FileNotFoundError:  If the file is missing. You need to run the setup script first.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Customer pool file not found: {path}\n"
            "Run generate_pools.py first to build the pool."
        )
    with path.open("r", encoding="utf-8") as f:
        pool = []
        for c in json.load(f):
            pool.append(Customer(**c))
        return pool
