# Bronze Layer

The Bronze layer ingests all incoming data. Ride records (`eh_rides`, `historical_rides`) are stored without modification. Mapping tables (`map_*`) have a `loaded_at` timestamp added on ingestion, and only new or changed rows are appended. All tables are stored as Delta tables in the `ride_hailing.bronze` schema.

---

## Tables

- [eh_rides](#eh_rides)
- [historical_rides](#historical_rides)
- [historical_rides_manifest](#historical_rides_manifest)
- [map_provinces](#map_provinces)
- [map_ride_options](#map_ride_options)
- [map_payment_methods](#map_payment_methods)
- [map_ride_statuses](#map_ride_statuses)
- [map_cancellation_reasons](#map_cancellation_reasons)

---

### eh_rides

**Source:** Azure Event Hub (real-time stream via Kafka)  
**Load method:** Streaming append (Delta Live Tables)  
**Purpose:** Landing table for real-time ride events. Each row represents one Kafka message. The ride payload is stored as a raw JSON string in the `records` column and parsed downstream in the Silver layer.

| Column Name | Data Type | Description |
|---|---|---|
| key | BINARY | Kafka message key (null for this source) |
| value | BINARY | Raw Kafka message bytes |
| topic | STRING | Event Hub topic name |
| partition | INTEGER | Kafka partition the message was written to |
| offset | LONG | Message position within the partition |
| timestamp | TIMESTAMP | Kafka ingestion timestamp |
| timestampType | INTEGER | Kafka timestamp type flag |
| headers | ARRAY | Kafka message headers |
| records | STRING | Decoded JSON string containing the ride record |

---

### historical_rides

**Source:** Azure Data Lake Storage Gen2 (CSV and JSON files)  
**Load method:** Incremental batch load  
**Purpose:** Stores historical ride records uploaded as files. Only new or replaced files are loaded each run, tracked by the `historical_rides_manifest`.

| Column Name | Data Type | Description |
|---|---|---|
| ride_id | STRING | Unique identifier for the ride (ULID) |
| booker_id | STRING | Unique identifier for the passenger |
| driver_id | STRING | Unique identifier for the driver |
| vehicle_id | STRING | Unique identifier for the vehicle |
| ride_status_id | INTEGER | Foreign key to map_ride_statuses |
| pickup_city_id | STRING | Province ID for the pickup location |
| dropoff_city_id | STRING | Province ID for the dropoff location |
| ride_option_id | INTEGER | Foreign key to map_ride_options |
| payment_method_id | INTEGER | Foreign key to map_payment_methods |
| booking_timestamp | STRING | Timestamp when the ride was booked (raw string) |
| pickup_latitude | DOUBLE | Latitude of the pickup point |
| pickup_longitude | DOUBLE | Longitude of the pickup point |
| pickup_address | STRING | Full pickup address |
| dropoff_latitude | DOUBLE | Latitude of the dropoff point |
| dropoff_longitude | DOUBLE | Longitude of the dropoff point |
| dropoff_address | STRING | Full dropoff address |
| booker_name | STRING | Full name of the passenger (PII) |
| booker_email | STRING | Email address of the passenger (PII) |
| booker_phone | STRING | Phone number of the passenger (PII) |
| driver_name | STRING | Full name of the driver (PII) |
| driver_phone | STRING | Phone number of the driver (PII) |
| driver_license | STRING | Driver's license number (PII) |
| vehicle_license_plate | STRING | Vehicle license plate (PII) |
| cancellation_reason_id | INTEGER | Foreign key to map_cancellation_reasons (null if completed) |
| travel_distance_km | DOUBLE | Trip distance in kilometres |
| duration_minutes | INTEGER | Trip duration in minutes |
| passenger_count | INTEGER | Number of passengers on the ride |
| pickup_timestamp | STRING | Timestamp when the ride was picked up (raw string) |
| dropoff_timestamp | STRING | Timestamp when the ride was dropped off (raw string) |
| driver_rating | DOUBLE | Driver's average rating (3.5–5.0) |
| rating | INTEGER | Passenger's rating for this ride (1–5) |
| base_fare | DOUBLE | Fixed base fare in Thai Baht |
| distance_fare | DOUBLE | Fare component based on distance |
| time_fare | DOUBLE | Fare component based on duration |
| surge_multiplier | DOUBLE | Surge pricing multiplier applied (1.0 = no surge) |
| subtotal | DOUBLE | Total fare before tip |
| tip_amount | DOUBLE | Optional tip added by the passenger |
| total_fare | DOUBLE | Final fare including tip |

---

### historical_rides_manifest

**Purpose:** Audit table that tracks every file loaded into `historical_rides`. A file is considered changed if its size differs from the recorded value, and only new or changed files are loaded each run.

| Column Name | Data Type | Description |
|---|---|---|
| file_path | STRING | Full ADLS path to the source file |
| file_name | STRING | File name only (e.g. historical_20260101_20260201.csv) |
| file_size | LONG | File size in bytes at the time of load |
| record_count | LONG | Number of records loaded from this file |
| loaded_at | TIMESTAMP | Timestamp when this file was processed |

---

### map_provinces

**Source:** Azure Data Lake Storage Gen2 - `map_provinces.json`  
**Load method:** Incremental append (change-detected)  
**Purpose:** Reference table of all 77 Thai provinces with their ISO 3166-2 identifiers.

| Column Name | Data Type | Description |
|---|---|---|
| province_id | STRING | ISO 3166-2 province code (e.g. TH-10 for Bangkok) |
| province_name | STRING | English name of the province |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |

---

### map_ride_options

**Source:** Azure Data Lake Storage Gen2 - `map_ride_options.json`  
**Load method:** Incremental append (change-detected)  
**Purpose:** Reference table of available ride options with their pricing rates and vehicle details. History is preserved - if a ride option is updated, the old row stays and a new row is appended with the new values.

| Column Name | Data Type | Description |
|---|---|---|
| ride_option_id | INTEGER | Unique identifier for the ride option |
| ride_option_name | STRING | Display name (e.g. Economy, Premium, Van) |
| vehicle_class | STRING | Vehicle category (e.g. Sedan, SUV, Motorcycle) |
| passenger_capacity | INTEGER | Maximum number of passengers |
| base_rate | DOUBLE | Fixed base fare in Thai Baht |
| per_km | DOUBLE | Fare per kilometre in Thai Baht |
| per_minute | DOUBLE | Fare per minute in Thai Baht |
| is_active | BOOLEAN | Whether this ride option is currently available |
| retired_at | STRING | Date the option was retired (null if still active) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |

---

### map_payment_methods

**Source:** Azure Data Lake Storage Gen2 - `map_payment_methods.json`  
**Load method:** Incremental append (change-detected)  
**Purpose:** Reference table of accepted payment methods. History is preserved across updates.

| Column Name | Data Type | Description |
|---|---|---|
| payment_method_id | INTEGER | Unique identifier for the payment method |
| payment_method | STRING | Display name (e.g. Cash, Credit Card, PromptPay) |
| is_card | BOOLEAN | True if the method is card-based |
| requires_auth | BOOLEAN | True if the method requires authentication (PIN, OTP, etc.) |
| is_active | BOOLEAN | Whether this payment method is currently accepted |
| retired_at | STRING | Date the method was retired (null if still active) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |

---

### map_ride_statuses

**Source:** Azure Data Lake Storage Gen2 - `map_ride_statuses.json`  
**Load method:** Incremental append (change-detected)  
**Purpose:** Reference table of possible ride statuses (Completed or Cancelled).

| Column Name | Data Type | Description |
|---|---|---|
| ride_status_id | INTEGER | Unique identifier for the status |
| ride_status | STRING | Status label (Completed, Cancelled) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |

---

### map_cancellation_reasons

**Source:** Azure Data Lake Storage Gen2 - `map_cancellation_reasons.json`  
**Load method:** Incremental append (change-detected)  
**Purpose:** Reference table of cancellation reasons with the responsible party. Row 1 (`cancellation_reason_id = 1`) represents a completed ride and has null values for initiator and reason.

| Column Name | Data Type | Description |
|---|---|---|
| cancellation_reason_id | INTEGER | Unique identifier for the cancellation reason |
| initiator | STRING | Party responsible for the cancellation (Driver, Passenger, System - null for completed rides) |
| cancellation_reason | STRING | Description of why the ride was cancelled (null for completed rides) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |
