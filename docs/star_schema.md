> Copy the code below and paste it into [dbdiagram.io](https://dbdiagram.io) to generate your star schema diagram.

Table fact_rides {
  ride_id string [pk]
  booker_id string [ref: > dim_booker.booker_id]
  driver_id string [ref: > dim_driver.driver_id]
  vehicle_id string [ref: > dim_vehicle.vehicle_id]
  pickup_city_id string [ref: > dim_province.province_id]
  dropoff_city_id string [ref: > dim_province.province_id]
  ride_option_id integer [ref: > dim_ride_option.ride_option_id]
  payment_method_id integer [ref: > dim_payment_method.payment_method_id]
  ride_status_id integer [ref: > dim_ride_status.ride_status_id]
  cancellation_reason_id integer [ref: > dim_cancellation_reason.cancellation_reason_id]
  booking_timestamp timestamp
  pickup_timestamp timestamp
  dropoff_timestamp timestamp
  booking_date date
  booking_hour integer
  pickup_latitude double
  pickup_longitude double
  dropoff_latitude double
  dropoff_longitude double
  travel_distance_km double
  duration_minutes integer
  passenger_count integer
  base_fare double
  distance_fare double
  time_fare double
  surge_multiplier double
  subtotal double
  tip_amount double
  total_fare double
  driver_rating double
  rating integer
}

Table dim_booker {
  booker_id string [pk]
  booker_name string
  booker_email string
  booker_phone string
  booking_timestamp timestamp
}

Table dim_driver {
  driver_id string [pk]
  driver_name string
  driver_phone string
  driver_license string
  booking_timestamp timestamp
}

Table dim_vehicle {
  vehicle_id string [pk]
  vehicle_license_plate string
  booking_timestamp timestamp
}

Table dim_province {
  province_id string [pk]
  province_name string
  loaded_at timestamp
}

Table dim_ride_status {
  ride_status_id integer [pk]
  ride_status string
  loaded_at timestamp
}

Table dim_cancellation_reason {
  cancellation_reason_id integer [pk]
  initiator string
  cancellation_reason string
  loaded_at timestamp
}

Table dim_ride_option {
  ride_option_id integer [pk]
  ride_option_name string
  vehicle_class string
  passenger_capacity integer
  base_rate double
  per_km double
  per_minute double
  is_active boolean
  retired_at string
  loaded_at timestamp
  __START_AT timestamp
  __END_AT timestamp
}

Table dim_payment_method {
  payment_method_id integer [pk]
  payment_method string
  is_card boolean
  requires_auth boolean
  is_active boolean
  retired_at string
  loaded_at timestamp
  __START_AT timestamp
  __END_AT timestamp
}