"""
Reads streaming live ride records from Azure Event Hub and saves them to the bronze table.

Source:  Azure Event Hub
Target:  Bronze table  (eh_rides)
"""

from pyspark import pipelines as dp
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Credentials are loaded from Databricks Secrets.
EH_NAMESPACE  = dbutils.secrets.get("ride-hailing", "eh-namespace")
EH_NAME       = dbutils.secrets.get("ride-hailing", "eh-name")
EH_CONN_STR   = dbutils.secrets.get("ride-hailing", "eh-connection-string")

KAFKA_OPTIONS = {
  "kafka.bootstrap.servers"  : f"{EH_NAMESPACE}.servicebus.windows.net:9093",
  "subscribe"                : EH_NAME,
  "kafka.sasl.mechanism"     : "PLAIN",
  "kafka.security.protocol"  : "SASL_SSL",
  "kafka.sasl.jaas.config"   : f"kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$ConnectionString\" password=\"{EH_CONN_STR}\";",
  "kafka.request.timeout.ms" : 10000,
  "kafka.session.timeout.ms" : 10000,
  "maxOffsetsPerTrigger"     : 10000,
  "failOnDataLoss"           : 'true',
  "startingOffsets"          : 'earliest'
}


@dp.table
def eh_rides():
    """
    Read ride records from Azure Event Hub.

    Each message contains one ride record as a JSON string.
    The message is decoded and stored in a column called 'records'.
    """
    df = spark.readStream.format("kafka")\
                .options(**KAFKA_OPTIONS)\
                .load()

    # Convert the raw message from bytes to a readable string.
    df = df.withColumn("records", col("value").cast("string"))
    return df