# =============================================================
# TelcoStream Lakehouse — Fase 9: Azure Extensions
# Catálogo: dbw_telcostream_dev
# =============================================================

# ---------------------------------------------------------------
# 9.1  Storage Credential + External Location (TEMPLATE)
# Substitua os placeholders antes de executar em produção.
# Requer: container ADLS separado + Service Principal Azure
# ---------------------------------------------------------------
# CREATE STORAGE CREDENTIAL telco_external_cred
#   WITH AZURE_SERVICE_PRINCIPAL (
#     DIRECTORY_ID  = dbutils.secrets.get('telcostream-scope', 'adls-tenant-id'),
#     APPLICATION_ID = dbutils.secrets.get('telcostream-scope', 'adls-client-id'),
#     CLIENT_SECRET = SECRET('telcostream-scope', 'adls-sp-secret')
#   );
#
# CREATE EXTERNAL LOCATION telco_external_raw
#   URL 'abfss://telcostream-external@<storage_account>.dfs.core.windows.net/raw'
#   WITH (STORAGE CREDENTIAL telco_external_cred)
#   COMMENT 'Landing zone externa para dados telco de terceiros';
#
# VALIDATE EXTERNAL LOCATION telco_external_raw;

# ---------------------------------------------------------------
# 9.2  External Table — snapshot Gold exportado para path externo
# Usa storage credential 'dbw_telcostream_dev' (cobre todo o storage)
# Substitua os placeholders abaixo antes de executar fora do ambiente original.
# ---------------------------------------------------------------
EXTERNAL_PATH = (
    "abfss://<UC_STORAGE_CONTAINER>@<UC_STORAGE_ACCOUNT>.dfs.core.windows.net"
    "/<WORKSPACE_ID>/external_lab/kpi_snapshot"
)

# Exportar Gold para Delta fora do __unitystorage
(
    spark.table("dbw_telcostream_dev.gold.kpi_tower_hourly")
    .write
    .format("delta")
    .mode("overwrite")
    .save(EXTERNAL_PATH)
)

# Criar external table apontando para o path exportado
spark.sql(f"""
  CREATE TABLE IF NOT EXISTS dbw_telcostream_dev.bronze.kpi_external_snapshot
  USING DELTA
  LOCATION '{EXTERNAL_PATH}'
  COMMENT 'External table — snapshot Gold exportado para ADLS externo (lab Fase 9)'
""")

count = spark.sql(
    "SELECT count(*) FROM dbw_telcostream_dev.bronze.kpi_external_snapshot"
).collect()[0][0]
print(f"External table OK — {count} linhas")

# ---------------------------------------------------------------
# 9.3  Secret Scope Databricks-backed
# Para AKV-backed: usar initial_manage_principal + Key Vault URI
# ---------------------------------------------------------------
import requests

ctx     = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
token   = ctx.apiToken().get()
host    = ctx.apiUrl().get()
headers = {"Authorization": f"Bearer {token}"}

# Criar scope (idempotente)
r = requests.post(
    f"{host}/api/2.0/secrets/scopes/create",
    headers=headers,
    json={"scope": "telcostream-scope", "initial_manage_principal": "users"}
)
if r.status_code == 200:
    print("Scope 'telcostream-scope' criado")
elif "RESOURCE_ALREADY_EXISTS" in r.text:
    print("Scope 'telcostream-scope' já existe")
else:
    raise RuntimeError(f"Erro ao criar scope: {r.status_code} {r.text}")

# Adicionar segredos (substitua pelos valores reais via Azure Key Vault / CI pipeline)
SECRETS = {
    "adls-tenant-id": "<TENANT_ID>",
    "adls-client-id": "<CLIENT_ID>",
    "adls-sp-secret": "<SP_SECRET>",
}
for key, val in SECRETS.items():
    requests.post(
        f"{host}/api/2.0/secrets/put",
        headers=headers,
        json={"scope": "telcostream-scope", "key": key, "string_value": val}
    )
    print(f"  secret '{key}' registrado")

# Demonstrar leitura segura (Databricks oculta o valor real em logs)
v = dbutils.secrets.get(scope="telcostream-scope", key="adls-tenant-id")
print(f"Leitura segura: adls-tenant-id = {'*' * len(v)} ({len(v)} chars)")

# Listar chaves do scope
print("\nChaves em 'telcostream-scope':")
for s in dbutils.secrets.list("telcostream-scope"):
    print(f"  {s.key}")
