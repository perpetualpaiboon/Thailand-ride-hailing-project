"""
Combines real-time and historical ride records into one silver table (rides_enriched).

Both sources go through the same steps before being written:
    - Date and time columns are converted from text to proper datetime values.
    - Personal information (names, phone numbers, emails, license plates)
      is replaced with a hash to protect user privacy.

Source:  Bronze tables  (eh_rides, historical_rides)
Target:  Silver table   (rides_enriched)
"""

from pyspark import pipelines as dp
from pyspark.sql.functions import col, from_json, sha2
from pyspark.sql.types import *

CATALOG         = "ride_hailing"
BRONZE_SCHEMA   = "bronze"

EH_RIDES_TABLE  = "eh_rides"
EH_RIDES_PATH   = f"{CATALOG}.{BRONZE_SCHEMA}.{EH_RIDES_TABLE}"

HISTORICAL_RIDES_TABLE  = "historical_rides"
HISTORICAL_RIDES_PATH   = f"{CATALOG}.{BRONZE_SCHEMA}.{HISTORICAL_RIDES_TABLE}"

TARGET_TABLE = "rides_enriched"

records_schema = StructType([
    StructField("ride_id",                  StringType(),  True),
    StructField("booker_id",                StringType(),  True),
    StructField("driver_id",                StringType(),  True),
    StructField("vehicle_id",               StringType(),  True),
    StructField("ride_status_id",           IntegerType(), True),
    StructField('pickup_city_id',           StringType(),  True),
    StructField('dropoff_city_id',          StringType(),  True),
    StructField("ride_option_id",           IntegerType(), True),
    StructField("payment_method_id",        IntegerType(), True),
    StructField("booking_timestamp",        StringType(),  True),
    StructField("pickup_latitude",          DoubleType(),  True),
    StructField("pickup_longitude",         DoubleType(),  True),
    StructField("pickup_address",           StringType(),  True),
    StructField("dropoff_latitude",         DoubleType(),  True),
    StructField("dropoff_longitude",        DoubleType(),  True),
    StructField("dropoff_address",          StringType(),  True),
    StructField("booker_name",              StringType(),  True),
    StructField("booker_email",             StringType(),  True),
    StructField("booker_phone",             StringType(),  True),
    StructField("driver_name",              StringType(),  True),
    StructField("driver_phone",             StringType(),  True),
    StructField("driver_license",           StringType(),  True),
    StructField("vehicle_license_plate",    StringType(),  True),
    StructField("cancellation_reason_id",   IntegerType(), True),
    StructField("travel_distance_km",       DoubleType(),  True),
    StructField("duration_minutes",         IntegerType(), True),
    StructField("passenger_count",          IntegerType(), True),
    StructField("pickup_timestamp",         StringType(),  True),
    StructField("dropoff_timestamp",        StringType(),  True),
    StructField("driver_rating",            DoubleType(),  True),
    StructField("rating",                   IntegerType(), True),
    StructField("base_fare",                DoubleType(),  True),
    StructField("distance_fare",            DoubleType(),  True),
    StructField("time_fare",                DoubleType(),  True),
    StructField("surge_multiplier",         DoubleType(),  True),
    StructField("subtotal",                 DoubleType(),  True),
    StructField("tip_amount",               DoubleType(),  True),
    StructField("total_fare",               DoubleType(),  True),
])

def _transform(df):
    """
    Prepare ride records before writing to the silver table.

    - Date and time columns are converted from text to proper datetime values.
    - Personal information (names, phone numbers, emails, license plates)
      is replaced with a hash to protect user privacy.
    """
    return (
        df
        .withColumn("booking_timestamp",    col("booking_timestamp").cast("timestamp"))
        .withColumn("pickup_timestamp",     col("pickup_timestamp").cast("timestamp"))
        .withColumn("dropoff_timestamp",    col("dropoff_timestamp").cast("timestamp"))
        .withColumn("booker_name",          sha2(col("booker_name"),            256))
        .withColumn("booker_email",         sha2(col("booker_email"),           256))
        .withColumn("booker_phone",         sha2(col("booker_phone"),           256))
        .withColumn("driver_name",          sha2(col("driver_name"),            256))
        .withColumn("driver_phone",         sha2(col("driver_phone"),           256))
        .withColumn("driver_license",       sha2(col("driver_license"),         256))
        .withColumn("vehicle_license_plate",sha2(col("vehicle_license_plate"),  256))
    )


dp.create_streaming_table(TARGET_TABLE)

@dp.append_flow(target=TARGET_TABLE)
def rides_stream():
    """
    Read live ride records coming in from Azure Event Hub.

    Each message is a JSON string. This function unpacks it into columns
    then passes it through _transform before writing.
    """
    df = spark.readStream.table(EH_RIDES_PATH)
    df_parsed = df.withColumn("parsed_records", from_json(col("records"), records_schema)) \
                  .select("parsed_records.*")
    return _transform(df_parsed)

@dp.append_flow(target=TARGET_TABLE)
def historical_flow():
    """
    Read historical ride records from the bronze table.

    Only new rows are picked up each run. Updates and deletes are ignored.
    """
    df = (
        spark.readStream
        .option("skipChangeCommits", "true")
        .table(HISTORICAL_RIDES_PATH)
    )
    return _transform(df)