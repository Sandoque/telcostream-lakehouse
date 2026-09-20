# TelcoStream Lakehouse — Ambiente e Evidências

## Workspace

| Campo | Valor |
|---|---|
| Workspace ID | `7405611591723186` |
| Host | `https://adb-7405611591723186.6.azuredatabricks.net` |
| Usuário | `acshinobi@outlook.com` |
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
| Conta ADLS | `dbstorageendatmjb73tym` |
| Container UC | `unity-catalog-storage` |
| Path raiz UC | `abfss://unity-catalog-storage@dbstorageendatmjb73tym.dfs.core.windows.net/7405611591723186` |
| Path managed | `…/__unitystorage/catalogs/788c33de-335c-4f28-a0db-f7e13c12bc36` |
| Path external lab | `…/7405611591723186/external_lab/kpi_snapshot` |
| Storage Credential (managed) | `dbw_telcostream_dev` |
| Storage Credential (externo) | `telco_external_cred` via Access Connector Managed Identity |
| External Location (managed) | `dbw_telcostream_dev` → `.../7405611591723186` |
| External Location (externo) | `telco_external_raw` → `abfss://telcostream-external@sttelcoextdev.dfs.core.windows.net/raw` |

## Recursos Azure Externos (mini lab Fase 9.5)

| Recurso Azure | Valor |
|---|---|
| Resource Group | `rg-telcostream-lab` |
| Storage Account | `sttelcoextdev` (LRS, ADLS Gen2, HNS habilitado) |
| Container | `telcostream-external` |
| Access Connector | `ac-telcostream-lab` |
| Access Connector Resource ID | `/subscriptions/f6ca658a-c0a3-43b3-b43c-f8b2c456885b/resourceGroups/rg-telcostream-lab/providers/Microsoft.Databricks/accessConnectors/ac-telcostream-lab` |
| RBAC | `Storage Blob Data Contributor` atribuído ao `ac-telcostream-lab` em `sttelcoextdev` |

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
