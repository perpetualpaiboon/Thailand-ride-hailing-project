# Silver Layer

The Silver layer combines and cleans data from the Bronze layer. Timestamps are cast to proper datetime types and all personally identifiable information (PII) is replaced with SHA-256 hashes before writing. All tables are stored as Delta tables in the `ride_hailing.silver` schema.

---

## Tables

- [rides_enriched](#rides_enriched)

---

### rides_enriched

**Source:** `bronze.eh_rides` (real-time stream) + `bronze.historical_rides` (batch)  
**Load method:** Delta Live Tables streaming append (two append flows merged into one target)  
**Purpose:** Unified ride record table combining both real-time and historical sources. Serves as the single source of truth for the Gold layer. PII columns are replaced with SHA-256 hashes to protect user privacy, the raw values are never stored here.

**PII columns hashed with SHA-256:** `booker_name`, `booker_email`, `booker_phone`, `driver_name`, `driver_phone`, `driver_license`, `vehicle_license_plate`

| Column Name | Data Type | Description |
|---|---|---|
| ride_id | STRING | Unique identifier for the ride (ULID) |
| booker_id | STRING | Unique identifier for the passenger |
| driver_id | STRING | Unique identifier for the driver |
| vehicle_id | STRING | Unique identifier for the vehicle |
| ride_status_id | INTEGER | Foreign key to bronze.map_ride_statuses |
| pickup_city_id | STRING | Province ID for the pickup location |
| dropoff_city_id | STRING | Province ID for the dropoff location |
| ride_option_id | INTEGER | Foreign key to bronze.map_ride_options |
| payment_method_id | INTEGER | Foreign key to bronze.map_payment_methods |
| booking_timestamp | TIMESTAMP | Timestamp when the ride was booked |
| pickup_latitude | DOUBLE | Latitude of the pickup point |
| pickup_longitude | DOUBLE | Longitude of the pickup point |
| pickup_address | STRING | Full pickup address |
| dropoff_latitude | DOUBLE | Latitude of the dropoff point |
| dropoff_longitude | DOUBLE | Longitude of the dropoff point |
| dropoff_address | STRING | Full dropoff address |
| booker_name | STRING | SHA-256 hash of the passenger's full name |
| booker_email | STRING | SHA-256 hash of the passenger's email address |
| booker_phone | STRING | SHA-256 hash of the passenger's phone number |
| driver_name | STRING | SHA-256 hash of the driver's full name |
| driver_phone | STRING | SHA-256 hash of the driver's phone number |
| driver_license | STRING | SHA-256 hash of the driver's license number |
| vehicle_license_plate | STRING | SHA-256 hash of the vehicle's license plate |
| cancellation_reason_id | INTEGER | Foreign key to bronze.map_cancellation_reasons (null if completed) |
| travel_distance_km | DOUBLE | Trip distance in kilometres |
| duration_minutes | INTEGER | Trip duration in minutes |
| passenger_count | INTEGER | Number of passengers on the ride |
| pickup_timestamp | TIMESTAMP | Timestamp when the ride was picked up |
| dropoff_timestamp | TIMESTAMP | Timestamp when the ride was dropped off |
| driver_rating | DOUBLE | Driver's average rating (3.5–5.0) |
| rating | INTEGER | Passenger's rating for this ride (1–5) |
| base_fare | DOUBLE | Fixed base fare in Thai Baht |
| distance_fare | DOUBLE | Fare component based on distance |
| time_fare | DOUBLE | Fare component based on duration |
| surge_multiplier | DOUBLE | Surge pricing multiplier applied (1.0 = no surge) |
| subtotal | DOUBLE | Total fare before tip |
| tip_amount | DOUBLE | Optional tip added by the passenger |
| total_fare | DOUBLE | Final fare including tip |
