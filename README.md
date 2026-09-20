# TelcoStream Lakehouse

Projeto de referência para o exame **DP-750 (Databricks Certified Data Engineer Professional)**  
e preparação para entrevista Capgemini/Vivo.  
Implementa um pipeline Medallião completo (Bronze → Silver → Gold) com Unity Catalog no Azure Databricks.

## Arquitetura

```
ADLS Gen2 (Volumes UC)
    │
    ├── Auto Loader (cloudFiles) ────► bronze.bronze_cdr          (1.149 linhas)
    └── COPY INTO               ────► bronze.customer_events     (110 linhas)
                                          │
                    MERGE (CTE inline, idempotente)
                                          │
                    ├──► silver.cdr_silver          (1.020 válidos)
                    ├──► silver.cdr_quarantine      (4 inválidos)
                    └──► silver.dim_customer_scd2   (110 versões, SCD Tipo 2)
                                          │
                    INSERT OVERWRITE PARTITION BY region
                                          │
                         ► gold.kpi_tower_hourly      (72 grupos hora/antena)
```

## Estrutura do Repositório

```
telcostream-lakehouse/
├── databricks.yml                  # Declarative Automation Bundle (DAB)
├── governance/
│   └── 08_governance.sql            # Column masks, row filter, GRANTs
├── azure/
│   └── 09_azure_extensions.py       # External table + secret scope
├── evidencias/
│   └── 00_ambiente.md               # Workspace, contagens, infra
└── docs/
    └── decisoes.md                  # Decisões técnicas documentadas
```

## Fases Implementadas

| Fase | Descrição | Status |
|---|---|---|
| 0 | Fundação: catálogo, schemas, volumes | ✅ |
| 1 | Silver: MERGE idempotente + quarentena | ✅ |
| 2 | Replay lote 02: Auto Loader + COPY INTO | ✅ |
| 3 | SCD2: dim_customer_scd2 | ✅ |
| 4 | Gold: KPIs particionados por region | ✅ |
| 5 | Pipeline Declarativo (SDP): `telcostream_sdp` | ✅ |
| 6 | Lakeflow Job: 3 tarefas, run 695010521785213 SUCCESS | ✅ |
| 7 | Git folder + Declarative Automation Bundle | ✅ |
| 8 | Governança: column mask, row filter, GRANTs | ✅ |
| 9 | Azure Extensions: external table, secret scope | ✅ (parcial) |
| 10 | Evidências para entrevista | ✅ |

## Recursos no Workspace

| Recurso | ID |
|---|---|
| Catálogo UC | `dbw_telcostream_dev` |
| Pipeline SDP | `d9fc5ce0-205f-4ba6-b008-23402cca1568` |
| Job (manual) | `699226207030057` |
| Job (bundle) | `742363202625953` |
| Workspace | `https://adb-7405611591723186.6.azuredatabricks.net` |

## Como Reproduzir

```bash
# Clonar e implantar via bundle
git clone https://github.com/Sandoque/telcostream-lakehouse
cd telcostream-lakehouse
databricks bundle validate --target dev
databricks bundle deploy   --target dev
```

Ver `evidencias/00_ambiente.md` para detalhes do ambiente e contagens.  
Ver `docs/decisoes.md` para decisões técnicas justificadas.