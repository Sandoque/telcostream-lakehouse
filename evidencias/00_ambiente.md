# TelcoStream Lakehouse — Ambiente e Evidências

## Workspace

| Campo | Valor |
|---|---|
| Workspace ID | `<WORKSPACE_ID>` |
| Host | `<WORKSPACE_HOST>` |
| Usuário | `<USER_EMAIL>` |
| Compute padrão | Serverless Interactive (CPU) |
| Região Azure | East US (inferida) |
| Unity Catalog | Habilitado |

## Catálogo e Schemas

**Catálogo:** `dbw_telcostream_dev`

| Schema | Finalidade |
|---|---|
| `bronze` | Dados brutos ingeridos (Auto Loader + COPY INTO) |
| `silver` | Dados validados, deduplicados e tipados |
| `gold` | KPIs agregados por antena/hora |
| `pipeline_lab` | Saída do pipeline SDP (`_sdp`) |
| `security` | Funções de governança (column masks, row filters) |
| `ops` | Estado do Auto Loader (checkpoint, schema evolution) |

## Storage

| Campo | Valor |
|---|---|
| Conta ADLS | `<UC_STORAGE_ACCOUNT>` |
| Container UC | `<UC_STORAGE_CONTAINER>` |
| Path raiz UC | `abfss://<UC_STORAGE_CONTAINER>@<UC_STORAGE_ACCOUNT>.dfs.core.windows.net/<WORKSPACE_ID>` |
| Path managed | `…/__unitystorage/catalogs/<UC_CATALOG_INTERNAL_ID>` |
| Path external lab | `…/<WORKSPACE_ID>/external_lab/kpi_snapshot` |
| Storage Credential (managed) | `dbw_telcostream_dev` |
| Storage Credential (externo) | `telco_external_cred` via Access Connector Managed Identity |
| External Location (managed) | `dbw_telcostream_dev` → `.../<WORKSPACE_ID>` |
| External Location (externo) | `telco_external_raw` → `abfss://<EXTERNAL_CONTAINER>@<EXTERNAL_STORAGE_ACCOUNT>.dfs.core.windows.net/raw` |

## Recursos Azure Externos (mini lab Fase 9.5)

| Recurso Azure | Valor |
|---|---|
| Resource Group | `<AZURE_RESOURCE_GROUP>` |
| Storage Account | `<EXTERNAL_STORAGE_ACCOUNT>` (LRS, ADLS Gen2, HNS habilitado) |
| Container | `<EXTERNAL_CONTAINER>` |
| Access Connector | `<ACCESS_CONNECTOR_NAME>` |
| Access Connector Resource ID | `/subscriptions/<AZURE_SUBSCRIPTION_ID>/resourceGroups/<AZURE_RESOURCE_GROUP>/providers/Microsoft.Databricks/accessConnectors/<ACCESS_CONNECTOR_NAME>` |
| RBAC | `Storage Blob Data Contributor` atribuído ao `<ACCESS_CONNECTOR_NAME>` em `<EXTERNAL_STORAGE_ACCOUNT>` |

## Volumes (Bronze)

| Volume | Finalidade |
|---|---|
| `bronze.raw_cdr_landing` | Landing zone CDR (JSON por lote) |
| `bronze.raw_customer_landing` | Landing zone clientes (CSV por lote) |
| `ops.pipeline_state` | Checkpoint e schema do Auto Loader |

## Contagens por Fase (verificado 2026-09-20)

| Fase | Tabela | Linhas |
|---|---|---|
| 0 – Bronze | `bronze.bronze_cdr` | **1.149** |
| 0 – Bronze | `bronze.customer_events` | **110** |
| 1 – Silver | `silver.cdr_silver` | **1.020** |
| 1 – Silver | `silver.cdr_quarantine` | **4** |
| 3 – SCD2 | `silver.dim_customer_scd2` | **110** (100 correntes) |
| 4 – Gold | `gold.kpi_tower_hourly` | **72** grupos hora/antena |
| 5 – SDP | `pipeline_lab.bronze_cdr_sdp` | **1.149** |
| 5 – SDP | `pipeline_lab.bronze_customers_sdp` | **110** |
| 5 – SDP | `pipeline_lab.cdr_silver_sdp` | **1.020** |
| 5 – SDP | `pipeline_lab.kpi_tower_hourly_sdp` | **72** |
| 9 – Azure | `bronze.kpi_external_snapshot` | **72** |
| 9 – Azure (ext) | `bronze.kpi_external_real` | **72** |

**Manifesto de reconciliação:** 1.149 Bronze = 1.020 Silver + 4 Quarentena + 125 Duplicatas ✅

## Job e Pipeline

| Recurso | ID | Status |
|---|---|---|
| Job `telcostream_pipeline_job` | `699226207030057` | Run 695010521785213 ✅ |
| Pipeline SDP `telcostream_sdp` | `d9fc5ce0-205f-4ba6-b008-23402cca1568` | Serverless, channel=CURRENT |
| Bundle Job (DAB) | `742363202625953` | Implantado via `bundle deploy` |

## Governança

| Item | Detalhe |
|---|---|
| Column Mask | `security.mask_pii` → `msisdn`, `document_id` em `cdr_silver` |
| Row Filter | `security.row_filter_tenant(tenant_id)` → isolamento por tenant |
| GRANTs | `USE CATALOG` / `USE SCHEMA gold` / `SELECT kpi_tower_hourly` |
| Secret Scope | `telcostream-scope` (Databricks-backed): `adls-tenant-id`, `adls-client-id`, `adls-sp-secret` |

## Git

| Campo | Valor |
|---|---|
| Repo | `https://github.com/Sandoque/telcostream-lakehouse` |
| Branch | `codex/telcostream-lab` |
| Bundle | `databricks.yml` na raiz |

---

## Evidências verificadas (2026-09-20)

### SHOW EXTERNAL LOCATIONS

| name | url | comment |
|---|---|---|
| `dbw_telcostream_dev` | `abfss://<UC_STORAGE_CONTAINER>@<UC_STORAGE_ACCOUNT>.dfs.core.windows.net/<WORKSPACE_ID>` | *(managed, sem comentário)* |
| `telco_external_raw` | `abfss://<EXTERNAL_CONTAINER>@<EXTERNAL_STORAGE_ACCOUNT>.dfs.core.windows.net/raw` | Landing zone externa fora do managed RG |

### SHOW STORAGE CREDENTIALS

| name | comment |
|---|---|
| `dbw_telcostream_dev` | *(managed, sem comentário)* |
| `telco_external_cred` | Credential de Managed Identity para o storage externo TelcoStream |

### DESCRIBE EXTENDED silver.cdr_silver — Governance (linhas-chave)

| col_name | valor |
|---|---|
| Row Filter | `` `dbw_telcostream_dev`.`security`.`row_filter_tenant` ON (tenant_id) `` |
| # Column Masks | *(seção)* |
| `msisdn` | `` `dbw_telcostream_dev`.`security`.`mask_pii` `` |
| `document_id` | `` `dbw_telcostream_dev`.`security`.`mask_pii` `` |
| Type | MANAGED |
| Owner | `<USER_EMAIL>` |
| Provider | delta |
| Comment | Eventos CDR validados, deduplicados e tipados — Silver |

### Contagens end-to-end (cell 10.1)

| fase | tabela | linhas |
|---|---|---|
| 0-Bronze | `bronze_cdr` | **1.149** |
| 0-Bronze | `customer_events` | **110** |
| 1-Silver | `cdr_quarantine` | **4** |
| 1-Silver | `cdr_silver` | **1.020** |
| 3-SCD2 | `dim_customer_scd2` | **110** |
| 4-Gold | `kpi_tower_hourly` | **72** |
| 5-SDP | `bronze_cdr_sdp` | **1.149** |
| 5-SDP | `bronze_customers_sdp` | **110** |
| 5-SDP | `cdr_silver_sdp` | **1.020** |
| 5-SDP | `kpi_tower_hourly_sdp` | **72** |
| 9-Azure | `kpi_external_real` | **72** |
| 9-Azure | `kpi_external_snapshot` | **72** |
