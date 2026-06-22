# Gold Layer

The Gold layer contains the star schema used for reporting and analysis. It is built from the Silver layer and Bronze mapping tables using Delta Live Tables. All tables are stored as Delta tables in the `ride_hailing.gold` schema.

**SCD Type 1** - always reflects the latest known value. No history is kept; old values are overwritten.  
**SCD Type 2** - keeps a full history of changes. When a row changes, the old version is preserved and a new version is added.

---

## Tables

**Dimension tables**
- [dim_booker](#dim_booker)
- [dim_driver](#dim_driver)
- [dim_vehicle](#dim_vehicle)
- [dim_province](#dim_province)
- [dim_ride_status](#dim_ride_status)
- [dim_cancellation_reason](#dim_cancellation_reason)
- [dim_ride_option](#dim_ride_option)
- [dim_payment_method](#dim_payment_method)

**Fact table**
- [fact_rides](#fact_rides)

---

### dim_booker

**Source:** `silver.rides_enriched`  
**SCD Type:** 1 (latest value only, no history)  
**Purpose:** One row per unique passenger. Contains hashed contact details. Always reflects the most recent booking record for each booker.

| Column Name | Data Type | Description |
|---|---|---|
| booker_id | STRING | Primary key - unique identifier for the passenger |
| booker_name | STRING | SHA-256 hash of the passenger's full name |
| booker_email | STRING | SHA-256 hash of the passenger's email address |
| booker_phone | STRING | SHA-256 hash of the passenger's phone number |
| booking_timestamp | TIMESTAMP | Timestamp of the most recent booking used to sequence updates |

---

### dim_driver

**Source:** `silver.rides_enriched`  
**SCD Type:** 1 (latest value only, no history)  
**Purpose:** One row per unique driver. Contains hashed contact and license details. Always reflects the most recent record for each driver.

| Column Name | Data Type | Description |
|---|---|---|
| driver_id | STRING | Primary key - unique identifier for the driver |
| driver_name | STRING | SHA-256 hash of the driver's full name |
| driver_phone | STRING | SHA-256 hash of the driver's phone number |
| driver_license | STRING | SHA-256 hash of the driver's license number |
| booking_timestamp | TIMESTAMP | Timestamp of the most recent booking used to sequence updates |

---

### dim_vehicle

**Source:** `silver.rides_enriched`  
**SCD Type:** 1 (latest value only, no history)  
**Purpose:** One row per unique vehicle. The license plate is hashed for privacy.

| Column Name | Data Type | Description |
|---|---|---|
| vehicle_id | STRING | Primary key - unique identifier for the vehicle |
| vehicle_license_plate | STRING | SHA-256 hash of the vehicle's license plate |
| booking_timestamp | TIMESTAMP | Timestamp of the most recent booking used to sequence updates |

---

### dim_province

**Source:** `bronze.map_provinces`  
**SCD Type:** Static (full refresh, no history tracking)  
**Purpose:** Reference table of all 77 Thai provinces. Used for both pickup and dropoff location lookups in `fact_rides`.

| Column Name | Data Type | Description |
|---|---|---|
| province_id | STRING | Primary key - ISO 3166-2 code (e.g. TH-10 for Bangkok) |
| province_name | STRING | English name of the province |
| loaded_at | TIMESTAMP | Timestamp when this row was loaded into the Bronze layer |

---

### dim_ride_status

**Source:** `bronze.map_ride_statuses`  
**SCD Type:** Static (full refresh, no history tracking)  
**Purpose:** Reference table of ride completion statuses.

| Column Name | Data Type | Description |
|---|---|---|
| ride_status_id | INTEGER | Primary key - unique identifier for the status |
| ride_status | STRING | Status label: Completed or Cancelled |
| loaded_at | TIMESTAMP | Timestamp when this row was loaded into the Bronze layer |

---

### dim_cancellation_reason

**Source:** `bronze.map_cancellation_reasons`  
**SCD Type:** Static (full refresh, no history tracking)  
**Purpose:** Reference table of cancellation reasons and the responsible party. `cancellation_reason_id = 1` represents completed rides (initiator and reason are null).

| Column Name | Data Type | Description |
|---|---|---|
| cancellation_reason_id | INTEGER | Primary key - unique identifier for the reason |
| initiator | STRING | Party responsible: Driver, Passenger, or System (null for completed rides) |
| cancellation_reason | STRING | Description of why the ride was cancelled (null for completed rides) |
| loaded_at | TIMESTAMP | Timestamp when this row was loaded into the Bronze layer |

---

### dim_ride_option

**Source:** `bronze.map_ride_options`  
**SCD Type:** 2 (full history - tracks changes to `ride_option_name`, `is_active`, `retired_at`)  
**Purpose:** Reference table of ride options with full change history. Old rides always link back to the ride option version that was active at the time of booking. Additional SCD Type 2 columns (`__START_AT`, `__END_AT`) are added automatically by Delta Live Tables.

| Column Name | Data Type | Description |
|---|---|---|
| ride_option_id | INTEGER | Primary key - unique identifier for the ride option |
| ride_option_name | STRING | Display name (e.g. Economy, Premium, Van) |
| vehicle_class | STRING | Vehicle category (e.g. Sedan, SUV, Motorcycle) |
| passenger_capacity | INTEGER | Maximum number of passengers |
| base_rate | DOUBLE | Fixed base fare in Thai Baht |
| per_km | DOUBLE | Fare per kilometre in Thai Baht |
| per_minute | DOUBLE | Fare per minute in Thai Baht |
| is_active | BOOLEAN | Whether this ride option is currently available |
| retired_at | STRING | Date the option was retired (null if still active) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |
| __START_AT | TIMESTAMP | Timestamp when this version became active (added by Delta Live Tables) |
| __END_AT | TIMESTAMP | Timestamp when this version was superseded (null if current) |

---

### dim_payment_method

**Source:** `bronze.map_payment_methods`  
**SCD Type:** 2 (full history - tracks changes to `payment_method`, `is_active`, `retired_at`)  
**Purpose:** Reference table of payment methods with full change history. Old rides always link back to the payment method version that was active at the time of booking. Additional SCD Type 2 columns (`__START_AT`, `__END_AT`) are added automatically by Delta Live Tables.

| Column Name | Data Type | Description |
|---|---|---|
| payment_method_id | INTEGER | Primary key - unique identifier for the payment method |
| payment_method | STRING | Display name (e.g. Cash, Credit Card, PromptPay) |
| is_card | BOOLEAN | True if the method is card-based |
| requires_auth | BOOLEAN | True if the method requires authentication (PIN, OTP, etc.) |
| is_active | BOOLEAN | Whether this payment method is currently accepted |
| retired_at | STRING | Date the method was retired (null if still active) |
| loaded_at | TIMESTAMP | Timestamp when this version of the row was loaded |
| __START_AT | TIMESTAMP | Timestamp when this version became active (added by Delta Live Tables) |
| __END_AT | TIMESTAMP | Timestamp when this version was superseded (null if current) |

---

### fact_rides

**Source:** `silver.rides_enriched`  
**SCD Type:** 1 (deduplicated by `ride_id`, sequenced by `booking_timestamp`)  
**Grain:** One row per ride  
**Purpose:** Central fact table for all ride metrics and measures. References all dimension tables via foreign keys. Two derived time columns (`booking_date`, `booking_hour`) are added to support time-based aggregations without joining back to the timestamp.

| Column Name | Data Type | Description |
|---|---|---|
| ride_id | STRING | Primary key - unique identifier for the ride (ULID) |
| booker_id | STRING | Foreign key → dim_booker |
| driver_id | STRING | Foreign key → dim_driver |
| vehicle_id | STRING | Foreign key → dim_vehicle |
| pickup_city_id | STRING | Foreign key → dim_province (pickup location) |
| dropoff_city_id | STRING | Foreign key → dim_province (dropoff location) |
| ride_option_id | INTEGER | Foreign key → dim_ride_option |
| payment_method_id | INTEGER | Foreign key → dim_payment_method |
| ride_status_id | INTEGER | Foreign key → dim_ride_status |
| cancellation_reason_id | INTEGER | Foreign key → dim_cancellation_reason |
| booking_timestamp | TIMESTAMP | Timestamp when the ride was booked |
| pickup_timestamp | TIMESTAMP | Timestamp when the ride was picked up |
| dropoff_timestamp | TIMESTAMP | Timestamp when the ride was dropped off |
| booking_date | DATE | Date of booking (derived from booking_timestamp) |
| booking_hour | INTEGER | Hour of booking in 24-hour format (0–23) |
| pickup_latitude | DOUBLE | Latitude of the pickup point |
| pickup_longitude | DOUBLE | Longitude of the pickup point |
| dropoff_latitude | DOUBLE | Latitude of the dropoff point |
| dropoff_longitude | DOUBLE | Longitude of the dropoff point |
| travel_distance_km | DOUBLE | Trip distance in kilometres |
| duration_minutes | INTEGER | Trip duration in minutes |
| passenger_count | INTEGER | Number of passengers on the ride |
| base_fare | DOUBLE | Fixed base fare in Thai Baht |
| distance_fare | DOUBLE | Fare component based on distance |
| time_fare | DOUBLE | Fare component based on duration |
| surge_multiplier | DOUBLE | Surge pricing multiplier applied (1.0 = no surge) |
| subtotal | DOUBLE | Total fare before tip |
| tip_amount | DOUBLE | Optional tip added by the passenger |
| total_fare | DOUBLE | Final fare including tip |
| driver_rating | DOUBLE | Driver's average rating (3.5–5.0) |
| rating | INTEGER | Passenger's rating for this ride (1–5) |
