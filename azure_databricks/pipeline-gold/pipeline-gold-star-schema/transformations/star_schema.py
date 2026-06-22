"""
Builds the gold layer star schema from the silver rides_enriched table.

Creates the following tables:

    Dimension tables:
        dim_booker:                 one row per unique booker (SCD Type 1)
        dim_driver:                 one row per unique driver (SCD Type 1)
        dim_vehicle:                one row per unique vehicle (SCD Type 1)
        dim_province:               list of provinces (static)
        dim_ride_status:            list of ride statuses (static)
        dim_cancellation_reason:    list of cancellation reasons (static)
        dim_ride_option:            ride options with history tracked (SCD Type 2)
        dim_payment_method:         payment methods with history tracked (SCD Type 2)

    Fact table:
        fact_rides:                 one row per ride with all measures and foreign keys

SCD Type 1: always reflects the latest known value, no history kept.
SCD Type 2: keeps a full history of changes over time.

Source:  Silver table   (rides_enriched)
         Bronze tables  (map_provinces, map_ride_statuses, map_cancellation_reasons,
                         map_ride_options, map_payment_methods)
Target:  Gold tables    (dim_*, fact_rides)

"""

from pyspark import pipelines as dp
from pyspark.sql.functions import col, hour

CATALOG         = "ride_hailing"
BRONZE_SCHEMA   = "bronze"
SILVER_SCHEMA   = "silver"

BRONZE_PATH         = f"{CATALOG}.{BRONZE_SCHEMA}"
RIDES_ENRICHED_PATH = f"{CATALOG}.{SILVER_SCHEMA}.rides_enriched"


# --- Dim Booker ---

@dp.view
def dim_booker_view():
    """Return one row per unique booker with their contact details."""
    return (
        spark.readStream
        .option("skipChangeCommits", "true")
        .option("ignoreDeletes", "true")
        .table(RIDES_ENRICHED_PATH)
        .select("booker_id", "booker_name", "booker_email", "booker_phone", "booking_timestamp")
        .dropDuplicates(["booker_id"])
    )

dp.create_streaming_table("dim_booker")
dp.create_auto_cdc_flow(
    target             = "dim_booker",
    source             = "dim_booker_view",
    keys               = ["booker_id"],
    sequence_by        = "booking_timestamp",
    stored_as_scd_type = 1,
)


# --- Dim Driver ---

@dp.view
def dim_driver_view():
    """Return one row per unique driver with their contact and license details."""
    return (
        spark.readStream
        .option("skipChangeCommits", "true")
        .option("ignoreDeletes", "true")
        .table(RIDES_ENRICHED_PATH)
        .select("driver_id", "driver_name", "driver_phone", "driver_license", "booking_timestamp")
        .dropDuplicates(["driver_id"])
    )

dp.create_streaming_table("dim_driver")
dp.create_auto_cdc_flow(
    target             = "dim_driver",
    source             = "dim_driver_view",
    keys               = ["driver_id"],
    sequence_by        = "booking_timestamp",
    stored_as_scd_type = 1,
)


# --- Dim Vehicle ---

@dp.view
def dim_vehicle_view():
    """Return one row per unique vehicle with its license plate."""
    return (
        spark.readStream
        .option("skipChangeCommits", "true")
        .option("ignoreDeletes", "true")
        .table(RIDES_ENRICHED_PATH)
        .select("vehicle_id", "vehicle_license_plate", "booking_timestamp")
        .dropDuplicates(["vehicle_id"])
    )

dp.create_streaming_table("dim_vehicle")
dp.create_auto_cdc_flow(
    target             = "dim_vehicle",
    source             = "dim_vehicle_view",
    keys               = ["vehicle_id"],
    sequence_by        = "booking_timestamp",
    stored_as_scd_type = 1,
)


# --- Dim Province (static) ---

@dp.table
def dim_province():
    """Return the full list of provinces from the bronze mapping table."""
    return spark.read.table(f"{BRONZE_PATH}.map_provinces")


# --- Dim Ride Status (static) ---

@dp.table
def dim_ride_status():
    """Return the full list of ride statuses from the bronze mapping table."""
    return spark.read.table(f"{BRONZE_PATH}.map_ride_statuses")


# --- Dim Cancellation Reason (static) ---

@dp.table
def dim_cancellation_reason():
    """Return the full list of cancellation reasons from the bronze mapping table."""
    return spark.read.table(f"{BRONZE_PATH}.map_cancellation_reasons")


# --- Dim Ride Option (SCD Type 2: tracks history) ---

@dp.view
def dim_ride_option_view():
    """
    Return ride option records for SCD Type 2 tracking.

    History is kept for name changes, active status, and retirement date
    so that old rides always link back to the correct version of the ride option.
    """
    return (
        spark.readStream
        .option("ignoreDeletes", "true")
        .table(f"{BRONZE_PATH}.map_ride_options")
        .select(
            "ride_option_id",
            "ride_option_name",
            "vehicle_class",
            "passenger_capacity",
            "base_rate",
            "per_km",
            "per_minute",
            "is_active",
            "retired_at",
            "loaded_at",
        )
    )

dp.create_streaming_table("dim_ride_option")
dp.create_auto_cdc_flow(
    target                    = "dim_ride_option",
    source                    = "dim_ride_option_view",
    keys                      = ["ride_option_id"],
    sequence_by               = "loaded_at",
    stored_as_scd_type        = 2,
    track_history_column_list = ["ride_option_name", "is_active", "retired_at"],
)


# --- Dim Payment Method (SCD Type 2: tracks history) ---

@dp.view
def dim_payment_method_view():
    """
    Return payment method records for SCD Type 2 tracking.

    History is kept for name changes, active status, and retirement date
    so that old rides always link back to the correct version of the payment method.
    """
    return (
        spark.readStream
        .option("ignoreDeletes", "true")
        .table(f"{BRONZE_PATH}.map_payment_methods")
        .select(
            "payment_method_id",
            "payment_method",
            "is_card",
            "requires_auth",
            "is_active",
            "retired_at",
            "loaded_at",
        )
    )

dp.create_streaming_table("dim_payment_method")
dp.create_auto_cdc_flow(
    target                    = "dim_payment_method",
    source                    = "dim_payment_method_view",
    keys                      = ["payment_method_id"],
    sequence_by               = "loaded_at",
    stored_as_scd_type        = 2,
    track_history_column_list = ["payment_method", "is_active", "retired_at"],
)

# --- Fact Rides ---
@dp.view
def fact_rides_view():
    """
    Return one row per ride with all measures and foreign keys.

    Extra columns are added for time-based reporting:
        booking_date:   the date the ride was booked
        booking_hour:   the hour of day the ride was booked (0-23)
    """
    return (
        spark.readStream
        .option("skipChangeCommits", "true")
        .option("ignoreDeletes", "true")
        .table(RIDES_ENRICHED_PATH)
        .select(
            "ride_id", 
            "booker_id", 
            "driver_id", 
            "vehicle_id",
            "pickup_city_id", 
            "dropoff_city_id",
            "ride_option_id", 
            "payment_method_id",
            "ride_status_id", 
            "cancellation_reason_id",

            "booking_timestamp", 
            "pickup_timestamp", 
            "dropoff_timestamp",

            "pickup_latitude", 
            "pickup_longitude",
            "dropoff_latitude", 
            "dropoff_longitude",

            "travel_distance_km", 
            "duration_minutes", 
            "passenger_count",
            "base_fare", 
            "distance_fare", 
            "time_fare",
            "surge_multiplier", 
            "subtotal", 
            "tip_amount", 
            "total_fare",
            "driver_rating", 
            "rating",
        )
        .withColumn("booking_date",     col("booking_timestamp").cast("date"))
        .withColumn("booking_hour",     hour(col("booking_timestamp")))
    )

dp.create_streaming_table("fact_rides")
dp.create_auto_cdc_flow(
    target             = "fact_rides",
    source             = "fact_rides_view",
    keys               = ["ride_id"],
    sequence_by        = "booking_timestamp",
    stored_as_scd_type = 1,
)
