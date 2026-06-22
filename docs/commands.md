# Commands

## generate_pools.py

```bash
# Generate driver and customer pools with pool sizes specified in
# driver_pool_size and customer_pool_size in generator/config.py
python generate_pools.py
```

## data_generator.py

```bash
# Print 5 records to terminal
python data_generator.py generate --count 5

# Generate historical batch and save to CSV
python data_generator.py historical --count 25000 --format csv --duration 2026-01-01:2026-02-01

# Generate historical batch and save to JSON
python data_generator.py historical --count 25000 --format json --duration 2026-01-01:2026-02-01

# Generate historical batch using saved pools (recommended after running generate_pools.py)
python data_generator.py historical --count 25000 --format csv --duration 2026-01-01:2026-02-01 --driver-pool data/pools/driver_pool_500.json --customer-pool data/pools/customer_pool_5000.json

# Send one record to Azure Event Hub
python data_generator.py eventhub --mode single

# Stream records to Azure Event Hub continuously
python data_generator.py eventhub --mode stream --interval 0.5
```

## upload_historical.py

```bash
# Upload all historical files to Azure Data Lake Storage Gen2
python upload_historical.py

# Upload files within a specific date range
python upload_historical.py --from-date 20260101 --to-date 20260601

# Upload specific files by name
python upload_historical.py --files historical_20260101_20260201.csv historical_20260201_20260301.csv
```
