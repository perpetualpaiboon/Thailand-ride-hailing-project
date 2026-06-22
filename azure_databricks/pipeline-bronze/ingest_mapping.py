"""
Reads mapping tables from Azure storage and loads them into the bronze layer.

Mapping tables contain reference data such as provinces, ride options,
payment methods, ride statuses, and cancellation reasons.

Only new or changed rows are written on each run. A row is considered changed
when its content is different from the last known version in the target table.
Unchanged rows are skipped.

Source:  Azure Data Lake Storage  (bronze/mapping_data/)
Target:  Bronze tables  (map_provinces, map_payment_methods, map_ride_options, map_ride_statuses, map_cancellation_reasons)
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window


# --- Configuration ---

ADLS_MAPPING_PREFIX         = "bronze/mapping_data"
ADLS_CONTAINER_NAME         = "ride-hailing-lake"
ADLS_STORAGE_ACCOUNT_NAME   = "stridehailing"

ADLS_PATH = f"abfss://{ADLS_CONTAINER_NAME}@{ADLS_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/{ADLS_MAPPING_PREFIX}"

BRONZE_SCHEMA = "ride_hailing.bronze"

# Primary key per mapping table: used to identify the latest known state.
TABLE_KEYS = {
    "map_provinces":            "province_id",
    "map_payment_methods":      "payment_method_id",
    "map_ride_options":         "ride_option_id",
    "map_ride_statuses":        "ride_status_id",
    "map_cancellation_reasons": "cancellation_reason_id",
}


# --- Functions ---

_HASH_COL   = "_row_hash"
_EXIST_HASH = "_existing_hash"
_RANK_COL   = "_rank"


def _add_content_hash(df, key_col: str) -> "DataFrame":
    """
    Add a fingerprint column that represents the content of each row.

    The fingerprint is calculated from all columns except the primary key
    and loaded_at. If any value in a row changes, its fingerprint changes too.
    This is used to detect which rows are new or different without comparing
    every column individually.
    """
    business_cols = sorted(
        c 
        for c in df.columns 
        if c not in (key_col, "loaded_at")
    )
    return df.withColumn(
        _HASH_COL,
        F.sha2(F.concat_ws("|", *[F.col(c).cast("string") for c in business_cols]), 256),
    )


def _latest_snapshot(existing_df, key_col: str) -> "DataFrame":
    """
    Return the most recently loaded version of each row from the target table.

    For each unique key, only the latest record is kept. The result includes
    the key and its fingerprint, which is used to compare against the source.
    """
    business_cols = sorted(
        c 
        for c in existing_df.columns 
        if c not in (key_col, "loaded_at")
    )
    window = Window.partitionBy(key_col).orderBy(F.col("loaded_at").desc())

    return (
        existing_df.withColumn(
            _EXIST_HASH,
            F.sha2(F.concat_ws("|", *[F.col(c).cast("string") for c in business_cols]), 256),
        )
        .withColumn(_RANK_COL, F.rank().over(window))
        .filter(F.col(_RANK_COL) == 1)
        .select(key_col, _EXIST_HASH)
    )


def _detect_changes(source_df, existing_df, key_col: str) -> "DataFrame":
    """
    Return only rows from the source that are new or have changed.

    A row is included if:
        - its key does not exist in the target table yet, OR
        - its content is different from the last known version.
    """
    latest = _latest_snapshot(existing_df, key_col)

    return (
        source_df
        .join(latest, on=key_col, how="left")
        .filter(
            F.col(_EXIST_HASH).isNull()                 # new key
            | (F.col(_HASH_COL) != F.col(_EXIST_HASH))  # changed content
        )
        .drop(_HASH_COL, _EXIST_HASH)
    )


# --- Ingestion loop ---

for table_name, key_col in TABLE_KEYS.items():
    target_table    = f"{BRONZE_SCHEMA}.{table_name}"
    source_path     = f"{ADLS_PATH}/{table_name}.json"

    # Read the JSON file from Azure storage for specific mapping table.
    source_df = spark.read.option("multiLine", True).json(source_path)
    source_df = _add_content_hash(source_df, key_col)

    if not spark.catalog.tableExists(target_table):
        # Initial load: if table does not exist yet, write all records on first run.
        (
            source_df
            .drop(_HASH_COL)
            .withColumn("loaded_at", F.current_timestamp())
            .write.format("delta")
            .mode("append")
            .saveAsTable(target_table)
        )
        print(f"[INITIAL LOAD] {table_name}: all records written.")

    else:
        # Updated loads: append only changed rows 
        existing_df   = spark.read.table(target_table)
        changed_df    = _detect_changes(source_df, existing_df, key_col)
        changed_count = changed_df.count()

        if changed_count > 0:
            (
                changed_df
                .withColumn("loaded_at", F.current_timestamp())
                .write.format("delta")
                .mode("append")
                .option("mergeSchema", "true")
                .saveAsTable(target_table)
            )
            print(f"[UPDATED] {table_name}: {changed_count} changed record(s) appended.")
        else:
            print(f"[NO CHANGE] {table_name}: source matches current state, nothing written.")
