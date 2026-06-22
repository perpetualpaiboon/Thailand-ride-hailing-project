# Sources

The Sources layer contains raw data before it enters the Bronze layer. Data originates from two places: the data generator (ride records) and the repository mapping files (reference data).

---

## Tables

- [ride_record (Event Hub / CSV / JSON)](#ride_record)
- [map_provinces](#map_provinces)
- [map_ride_options](#map_ride_options)
- [map_payment_methods](#map_payment_methods)
- [map_ride_statuses](#map_ride_statuses)
- [map_cancellation_reasons](#map_cancellation_reasons)

---

### ride_record

**Source:** Data generator (`data_generator.py`)  
**Formats:** JSON (streamed to Azure Event Hubs) · CSV or JSON (saved as historical batch files)  
**Purpose:** Raw ride records produced by the data generator. Real-time records are sent to Azure Event Hubs one message at a time. Historical records are saved as flat files and uploaded to Azure Data Lake Storage Gen2. Both formats share the same field structure.

| Column Name | Data Type | Description |
|---|---|---|
| ride_id | STRING | Unique identifier for the ride (ULID) |
| booker_id | STRING | Unique identifier for the passenger |
| driver_id | STRING | Unique identifier for the driver |
| vehicle_id | STRING | Unique identifier for the vehicle |
| ride_status_id | INTEGER | References map_ride_statuses |
| pickup_city_id | STRING | ISO 3166-2 province code for the pickup location |
| dropoff_city_id | STRING | ISO 3166-2 province code for the dropoff location |
| ride_option_id | INTEGER | References map_ride_options |
| payment_method_id | INTEGER | References map_payment_methods |
| booking_timestamp | STRING | Timestamp when the ride was booked (ISO 8601 string) |
| pickup_latitude | DOUBLE | Latitude of the pickup point |
| pickup_longitude | DOUBLE | Longitude of the pickup point |
| pickup_address | STRING | Full pickup address (Thai) |
| dropoff_latitude | DOUBLE | Latitude of the dropoff point |
| dropoff_longitude | DOUBLE | Longitude of the dropoff point |
| dropoff_address | STRING | Full dropoff address (Thai) |
| booker_name | STRING | Full name of the passenger (PII) |
| booker_email | STRING | Email address of the passenger (PII) |
| booker_phone | STRING | Phone number of the passenger (PII) |
| driver_name | STRING | Full name of the driver (PII) |
| driver_phone | STRING | Phone number of the driver (PII) |
| driver_license | STRING | Driver's license number (PII) |
| vehicle_license_plate | STRING | Vehicle license plate (PII) |
| cancellation_reason_id | INTEGER | References map_cancellation_reasons (null if completed) |
| travel_distance_km | DOUBLE | Trip distance in kilometres |
| duration_minutes | INTEGER | Trip duration in minutes |
| passenger_count | INTEGER | Number of passengers on the ride |
| pickup_timestamp | STRING | Timestamp when the ride was picked up (ISO 8601 string) |
| dropoff_timestamp | STRING | Timestamp when the ride was dropped off (ISO 8601 string) |
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

### map_provinces

**Source:** `data/mapping_data/map_provinces.json`  
**Purpose:** Reference table of all 77 Thai provinces with their ISO 3166-2 identifiers. Uploaded to Azure Data Lake Storage Gen2 via GitHub Actions.

| Column Name | Data Type | Description |
|---|---|---|
| province_id | STRING | ISO 3166-2 province code (e.g. TH-10 for Bangkok) |
| province_name | STRING | English name of the province |

---

### map_ride_options

**Source:** `data/mapping_data/map_ride_options.json`  
**Purpose:** Reference table of available ride options with their pricing rates and vehicle details.

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

---

### map_payment_methods

**Source:** `data/mapping_data/map_payment_methods.json`  
**Purpose:** Reference table of accepted payment methods.

| Column Name | Data Type | Description |
|---|---|---|
| payment_method_id | INTEGER | Unique identifier for the payment method |
| payment_method | STRING | Display name (e.g. Cash, Credit Card, PromptPay) |
| is_card | BOOLEAN | True if the method is card-based |
| requires_auth | BOOLEAN | True if the method requires authentication (PIN, OTP, etc.) |
| is_active | BOOLEAN | Whether this payment method is currently accepted |
| retired_at | STRING | Date the method was retired (null if still active) |

---

### map_ride_statuses

**Source:** `data/mapping_data/map_ride_statuses.json`  
**Purpose:** Reference table of possible ride statuses.

| Column Name | Data Type | Description |
|---|---|---|
| ride_status_id | INTEGER | Unique identifier for the status |
| ride_status | STRING | Status label (Completed, Cancelled) |

---

### map_cancellation_reasons

**Source:** `data/mapping_data/map_cancellation_reasons.json`  
**Purpose:** Reference table of cancellation reasons and the responsible party. `cancellation_reason_id = 1` represents completed rides and has null values for initiator and reason.

| Column Name | Data Type | Description |
|---|---|---|
| cancellation_reason_id | INTEGER | Unique identifier for the cancellation reason |
| initiator | STRING | Party responsible: Driver, Passenger, or System (null for completed rides) |
| cancellation_reason | STRING | Description of why the ride was cancelled (null for completed rides) |
