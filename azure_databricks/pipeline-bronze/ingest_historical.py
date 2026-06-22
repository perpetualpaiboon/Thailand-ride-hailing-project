"""
Reads historical ride CSV and JSON files from Azure storage and loads them into the bronze table.

Only new files are loaded each run. A manifest table keeps track of which files
have already been loaded, so the same file is never loaded twice.

Source:  Azure Data Lake Storage  (bronze/manual_uploads/historical_data/)
Target:  Bronze table  (historical_rides)
         Manifest table  (historical_rides_manifest)
"""

from pyspark.sql import functions as F, DataFrame
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, LongType, TimestampType,
)
from functools import reduce
 

# --- Configuration ---

ADLS_HISTORICAL_PREFIX    = "bronze/manual_uploads/historical_data"
ADLS_CONTAINER_NAME       = "ride-hailing-lake"
ADLS_STORAGE_ACCOUNT_NAME = "stridehailing"

ADLS_PATH = f"abfss://{ADLS_CONTAINER_NAME}@{ADLS_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/{ADLS_HISTORICAL_PREFIX}"

BRONZE_SCHEMA           = "ride_hailing.bronze"

TARGET_TABLE_NAME       = "historical_rides"
MANIFEST_TABLE_NAME     = "historical_rides_manifest"

TARGET_TABLE_PATH       = f"{BRONZE_SCHEMA}.{TARGET_TABLE_NAME}"
MANIFEST_TABLE_PATH     = f"{BRONZE_SCHEMA}.{MANIFEST_TABLE_NAME}"

# --- Schemas ---

rides_schema = StructType([
    StructField("ride_id",                  StringType(),  True),
    StructField("booker_id",                StringType(),  True),
    StructField("driver_id",                StringType(),  True),
    StructField("vehicle_id",               StringType(),  True),
    StructField("ride_status_id",           IntegerType(), True),
    StructField("pickup_city_id",           StringType(),  True),
    StructField("dropoff_city_id",          StringType(),  True),
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

manifest_schema = StructType([
    StructField("file_path",    StringType(),   False),
    StructField("file_name",    StringType(),   False),
    StructField("file_size",    LongType(),     True),
    StructField("record_count", LongType(),     False),
    StructField("loaded_at",    TimestampType(), False),
])


# --- Functions ---

def _get_loaded_files() -> set:
    """
    Return the set of files already recorded in the manifest table.

    Each entry is a (file_path, file_size) pair. Tracking file size means
    a file will be reloaded if it is replaced with a different version
    under the same name.
    """
    if not spark.catalog.tableExists(MANIFEST_TABLE_PATH):
        return set()

    return {
        (row.file_path, row.file_size)
        for row in spark.read.table(MANIFEST_TABLE_PATH).select("file_path", "file_size").collect()
    }


def _read_files(file_paths: list, fmt: str) -> DataFrame:
    """
    Read a list of files from Azure storage and return them as a single table.

    For CSV files, columns are matched by name from the header row, not by
    position. This prevents column misalignment if the file column order ever
    changes. Each column is then converted to its correct data type.

    For JSON files, columns are always matched by name automatically.
    """
    if fmt == "json":
        return spark.read.option("multiLine", True).schema(rides_schema).json(file_paths)

    if fmt == "csv":
        # Step 1: Read the CSV using the header row to match columns by name.
        # quote='"':    anything wrapped in "..." is treated as one single field, so commas inside are ignored 
        #               (e.g, "บ้านนาต้อง, นายูง, อำเภอนายูง, จังหวัดอุดรธานี, ประเทศไทย",18.015268431989394,102.06924787303511,"บ้านเพิ่ม, โนนทอง, อำเภอนายูง, จังหวัดอุดรธานี, ประเทศไทย")
        # escape='"':   if a double-quote appears inside a field, it is written as "" and Spark knows to read it as just one "
        df = (
            spark.read
            .option("header",  True)
            .option("quote",   '"')
            .option("escape",  '"')
            .csv(file_paths)
        )

        # Step 2: Convert each column to the type declared in rides_schema.
        # try_cast() is used so that any unreadable value becomes null instead of throwing an error.
        for field in rides_schema.fields:
            if field.name not in df.columns:
                continue
            type_str = field.dataType.simpleString()
            df = df.withColumn(
                field.name,
                F.expr(f"try_cast(`{field.name}` as {type_str})")
            )

        return df

    raise ValueError(f"Unsupported format: {fmt}")


def _write_manifest(entries: list) -> None:
    """Record the newly loaded files in the manifest table."""
    manifest_df = spark.createDataFrame(entries, schema=manifest_schema)
    (
        manifest_df.write
        .format("delta")
        .mode("append")
        .saveAsTable(MANIFEST_TABLE_PATH)
    )

# --- Incremental ingestion ---

# Step 1: Find all historical files currently in Azure storage.
all_files = dbutils.fs.ls(ADLS_PATH)

json_files = {f.path: f for f in all_files if f.name.endswith(".json")}
csv_files  = {f.path: f for f in all_files if f.name.endswith(".csv")}

# Step 2: Exclude files already recorded in the manifest (by path + size).
loaded = _get_loaded_files()

new_json = [f for path, f in json_files.items() if (path, f.size) not in loaded]
new_csv  = [f for path, f in csv_files.items()  if (path, f.size) not in loaded]

if not new_json and not new_csv:
    print("[NO NEW FILES] All files already loaded. Nothing to process.")
else:
    # Step 3: Read only new files.
    dfs = []
    if new_json:
        dfs.append(_read_files([f.path for f in new_json], "json"))
    if new_csv:
        dfs.append(_read_files([f.path for f in new_csv], "csv"))

    combined_df = reduce(DataFrame.unionByName, dfs)
    record_count = combined_df.count()

    if record_count == 0:
        print("[EMPTY FILES] New files found but produced zero records. Skipping.")
    else:
        # Step 4: Append new records to historical_rides.
        (
            combined_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .saveAsTable(TARGET_TABLE_PATH)
        )
        print(f"[LOADED] {record_count} record(s) appended → {TARGET_TABLE_PATH}")

        # Step 5: Log processed files in the manifest table.
        manifest_rows = []
        loaded_at_val = spark.sql("SELECT current_timestamp()").collect()[0][0]

        for f in new_json:
            df = _read_files([f.path], "json")
            cnt = df.count()
            manifest_rows.append((f.path, f.name, f.size, cnt, loaded_at_val))

        for f in new_csv:
            df = _read_files([f.path], "csv")
            cnt = df.count()
            manifest_rows.append((f.path, f.name, f.size, cnt, loaded_at_val))

        _write_manifest(manifest_rows)
        print(f"[MANIFEST] {len(manifest_rows)} file(s) recorded → {MANIFEST_TABLE_PATH}")
