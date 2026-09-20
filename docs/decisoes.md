# TelcoStream Lakehouse — Decisões Técnicas

Documento de decisões de design tomadas durante o projeto TelcoStream.
Finalidade: evidência técnica para Certificação DP-750.

---

## 1. CTE inline no MERGE (Fase 1)

**Decisão:** usar `WITH cte AS (…) MERGE INTO target USING cte …` em vez de `CREATE TEMP VIEW + MERGE`.

**Por quê:** Em Databricks SQL, TEMP VIEWs criadas em um statement não propagam para o próximo statement dentro da mesma cell. Usar CTE inline garante que a lógica de deduplicação é resolvida no escopo do MERGE, tornando o código autocontido e idempotente.

---

## 2. TRY_CAST para `data_mb` (Fase 1)

**Decisão:** substituir `CAST(data_mb AS DOUBLE) < 0` por `TRY_CAST(data_mb AS DOUBLE) < 0`.

**Por quê:** A coluna `data_mb` é ingerida como STRING. Registros com valores inválidos (ex: `"N/A"`) disparam `CAST_INVALID_INPUT` com `CAST`, abortando a query. `TRY_CAST` retorna `NULL` em caso de erro, permitindo que a lógica de quarentena trate esses casos sem falhar.

---

## 3. MERGE idempotente com `event_version` (Fase 1–2)

**Decisão:** na cláusula WHEN MATCHED do MERGE Silver, atualizar apenas quando `src.event_version > tgt.event_version`.

**Por quê:** Garante que re-execuções (replay) sejam seguras: uma versão mais antiga não sobrescreve uma versão mais recente. Isso permite processar lotes fora de ordem e repetir o MERGE sem efeitos colaterais.

---

## 4. `delta.feature.allowColumnDefaults` na SCD2 (Fase 3)

**Decisão:** adicionar `TBLPROPERTIES ('delta.feature.allowColumnDefaults' = 'supported')` na criação da tabela SCD2.

**Por quê:** A coluna `is_current BOOLEAN DEFAULT true` requer que o Delta feature de column defaults esteja habilitado. Sem essa propriedade, a cláusula `DEFAULT` é rejeitada no `CREATE TABLE`.

---

## 5. `schema` vs `target` no bundle YAML (Fase 7)

**Decisão:** usar `schema: pipeline_lab` em vez de `target: pipeline_lab` no recurso `pipelines` do `databricks.yml`.

**Por quê:** O pipeline `telcostream_sdp` foi criado com o campo `schema` (nova spec DLT). Quando o bundle usava `target:` (campo legado), o `bundle deploy` enviava `schema: null` na chamada `PUT /api/2.0/pipelines/{id}`, gerando erro `400 INVALID_PARAMETER_VALUE: Cannot unset 'schema' field once it's defined`. A solução foi alinhar o YAML ao campo usado na spec do pipeline existente.

---

## 6. Schema `pipeline_lab` para o SDP (Fase 5)

**Decisão:** mover o output do pipeline SDP de `default` para `pipeline_lab`.

**Por quê:** O schema `default` é compartilhado e pode conter objetos não relacionados ao projeto. Usar um schema dedicado (`pipeline_lab`) isola os objetos do SDP, facilita GRANTs específicos e evita colisão de nomes com tabelas manuais (ex: `cdr_silver` vs `cdr_silver_sdp`).

---

## 7. Auto Loader sem `schemaLocation` no SDP (Fase 5)

**Decisão:** não definir `cloudFiles.schemaLocation` nem `checkpointLocation` nas Streaming Tables do SDP.

**Por quê:** Em Lakeflow Spark Declarative Pipelines, o runtime gerencia automaticamente o checkpoint e o schema evolution. Definir essas opções manualmente causa conflito com o gerenciamento interno e pode travar o pipeline.

---

## 8. GRANTs ao usuário atual (fallback) em vez de grupo (Fase 8)

**Decisão:** aplicar GRANTs a `acshinobi@outlook.com` diretamente, em vez de ao grupo `telco_analysts`.

**Por quê:** `acshinobi@outlook.com` é conta pessoal Microsoft (outlook.com), não provisionada no tenant Azure do Account Console (`accounts.azuredatabricks.net`). UC exige grupos de nível de conta; grupos workspace-local criados via `WorkspaceClient` não são reconhecidos pelo UC. `AccountClient()` retornou `NotFound`. O fallback garante que o padrão de GRANT funciona para demonstração; em produção, criar o grupo no Account Console antes de executar.

---

## 9. Secret scope Databricks-backed (Fase 9)

**Decisão:** criar scope `telcostream-scope` via REST API (`/api/2.0/secrets/scopes/create`) como Databricks-backed, em vez de AKV-backed.

**Por quê:** Um secret scope AKV-backed requer um Azure Key Vault provisionado, permissões de `Get`/`List` via Azure RBAC e o URI do vault. No ambiente de lab com conta pessoal, o AKV não está disponível. O scope Databricks-backed demonstra o padrão de `dbutils.secrets.get` com a mesma API de leitura; a troca para AKV-backed em produção é apenas de configuração (sem mudança de código).

---

## 10. External table no mesmo storage (Fase 9)

**Decisão:** criar `bronze.kpi_external_snapshot` em `external_lab/kpi_snapshot` dentro do mesmo storage account UC, usando a storage credential existente.

**Por quê:** O workspace tem apenas uma storage account (`dbstorageendatmjb73tym`). Uma external location apontando para um container separado exigiria um segundo storage account com Service Principal dedicado. Usar um sub-path fora de `__unitystorage/` dentro da mesma conta demonstra o padrão de external table (arquivo Delta gerenciado pelo usuário, não pelo UC) sem precisar de infraestrutura adicional.
