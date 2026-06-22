## Azure Setup

**1. Create a Resource Group**

Create a single resource group to hold all project resources.

- Go to the [Azure Portal](https://portal.azure.com) → **Resource groups** → **Create**
- Choose a subscription, region, and name (e.g. `rg-ride-hailing`)

---

**2. Create Azure Data Lake Storage Gen2**

Used to store historical ride files and mapping data.

- Go to **Storage accounts** → **Create**
- Select the resource group created above
- Under **Advanced**, enable **Hierarchical namespace** (this enables ADLS Gen2)
- Once created, go to the storage account → **Containers** → create one container (e.g. `ride-hailing-lake`)
- The pipeline expects the following folder structure inside the container:
  - `bronze/manual_uploads/historical_data/` — for historical ride CSV/JSON files
  - `bronze/mapping_data/` — for province, ride option, and payment method JSON files

---

**3. Create Azure Event Hubs**

Used to receive real-time ride events from the data generator.

- Go to **Event Hubs** → **Create** → create a **Namespace**
- Select the resource group and choose a pricing tier (Basic or Standard)
- Inside the namespace, go to **Event Hubs** → **+ Event Hub** → create one named `eh-ride-hailing`

---

**4. Create Azure Databricks**

Used to run the Bronze, Silver, and Gold pipeline notebooks.

- Go to **Azure Databricks** → **Create**
- Select the resource group and a pricing tier (Standard or Premium)
- Once deployed, click **Launch Workspace**
- Inside the workspace, create a cluster to run the pipelines
- Connect the Databricks workspace to ADLS Gen2 and Event Hubs by storing credentials as Databricks secrets:

  **Install the Databricks CLI and authenticate**
  ```bash
  pip install databricks-cli
  databricks configure --token
  # Enter your Databricks workspace URL and a personal access token
  ```

  **Create a secret scope**
  ```bash
  databricks secrets create-scope --scope ride-hailing
  ```

  **Add secrets to the scope**
  ```bash
  databricks secrets put --scope ride-hailing --key eh-namespace
  databricks secrets put --scope ride-hailing --key eh-name
  databricks secrets put --scope ride-hailing --key eh-connection-string
  ```

  Secrets can then be read inside Databricks notebooks with:
  ```python
  dbutils.secrets.get(scope="ride-hailing", key="eh-connection-string")
  ```

---

## Local Setup

**1. Clone the repository**
```bash
git clone https://github.com/perpetualpaiboon/thailand-ride-hailing-project
cd thailand-ride-hailing-project
```

**2. Create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**
```bash
cp .env.example .env
# Fill in your Azure credentials
```

Fill in the following values in `.env`:

| Variable | Description |
|---|---|
| `EVENT_HUB_NAME` | Azure Event Hub name (e.g. `eh-ride-hailing`) |
| `EVENT_HUB_CONNECTION_STR` | Connection string from Azure Portal → Event Hub → Shared access policies |
| `STORAGE_ACCOUNT_CONTAINER_NAME` | Azure storage container name (e.g. `ride-hailing-lake`) |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string from Azure Portal → Storage Account → Access keys |


**5. Set up GitHub Actions secrets**

The `sync_mapping.yml` workflow uploads mapping JSON files to ADLS whenever they are updated in the repository. Add the following as repository secrets in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Same connection string as in `.env` |

**6. Start Nominatim Docker**
```bash
docker compose up -d
```

**7. Generate pools**
```bash
python generate_pools.py
```

**8. Generate data**
```bash
python data_generator.py historical --count 5000 --format csv --duration 2026-01-01:2026-02-01
```

**9. Upload to Azure**
```bash
python upload_historical.py
```

**10. Stream records to Azure Event Hub**
```bash
python data_generator.py eventhub --mode stream --interval 0.5
```

**11. Upload mapping data to ADLS**

Mapping data is uploaded automatically via GitHub Actions. Any commit that changes files under `data/mapping_data/` triggers `sync_mapping.yml`, which uploads the changed JSON files to `bronze/mapping_data/` in the ADLS container.

```bash
git add data/mapping_data/
git commit -m "update mapping data"
git push
```
