# Relatório Técnico — Projeto TelcoStream Lakehouse

## 1. Resumo executivo

Este documento consolida a implementação do projeto **TelcoStream Lakehouse** no Azure Databricks com **Unity Catalog**, com foco em dois objetivos:

* preparação para a certificação **DP-750 / Microsoft Certified: Azure Databricks Data Engineer Associate**
* suporte a uma **demonstração técnica profissional**, com evidências funcionais, arquiteturais e operacionais

O projeto implementa um fluxo **Medallion Architecture** completo, cobrindo ingestão de dados, transformação, qualidade, deduplicação, modelagem histórica, agregação analítica, orquestração, governança e integração com recursos Azure externos.

Ao final do lab, o ambiente ficou com:

* pipeline Bronze → Silver → Gold funcional
* histórico SCD Tipo 2 implementado
* pipeline declarativo e job orquestrado validados
* políticas de governança com **column mask** e **row filter** ativas
* integração com **external location** em storage externo real ao managed resource group
* documentação técnica, evidências e roteiro de demonstração prontos

---

## 2. Objetivo do projeto

O caso TelcoStream simula um cenário de engenharia de dados para telecom, em que eventos de chamadas e eventos de clientes precisam ser tratados com requisitos típicos de produção:

* ingestão incremental e idempotente
* deduplicação por versão de evento
* separação entre registros válidos e inválidos
* manutenção de histórico de atributos de cliente
* geração de KPIs de negócio
* governança de acesso com Unity Catalog
* automação por pipeline declarativo, job e bundle
* integração com Azure Data Lake Storage Gen2

Do ponto de vista de certificação e avaliação técnica, o projeto demonstra domínio prático de:

* modelagem lakehouse
* SQL e PySpark aplicados a Databricks
* Unity Catalog
* Lakeflow Jobs
* Lakeflow Spark Declarative Pipelines
* external locations e storage credentials
* boas práticas de validação e evidência técnica

---

## 3. Escopo técnico implementado

### 3.1 Ambiente

| Item | Valor |
| --- | --- |
| Workspace | `<WORKSPACE_HOST>` |
| Workspace ID | `<WORKSPACE_ID>` |
| Usuário | `<USER_EMAIL>` |
| Catálogo | `dbw_telcostream_dev` |
| Compute principal | Serverless Interactive |
| Região Azure | East US |

### 3.2 Schemas do catálogo

| Schema | Finalidade |
| --- | --- |
| `bronze` | ingestão bruta |
| `silver` | dados validados e tipados |
| `gold` | camadas analíticas e KPIs |
| `pipeline_lab` | saídas do pipeline declarativo |
| `security` | funções de governança |
| `ops` | estado/checkpoint de ingestão |

### 3.3 Arquitetura lógica

```text
ADLS Gen2 / Volumes UC
    │
    ├── Auto Loader (CDRs) ─────────────► bronze.bronze_cdr
    ├── COPY INTO (clientes) ───────────► bronze.customer_events
    │
    └── MERGE + validação + deduplicação
                          │
                          ├──► silver.cdr_silver
                          ├──► silver.cdr_quarantine
                          └──► silver.dim_customer_scd2
                                      │
                                      └──► gold.kpi_tower_hourly

Pipeline declarativo (pipeline_lab)
Lakeflow Job (3 etapas)
Governança UC (mask + row filter)
External Location Azure (storage externo real)
```

---

## 4. Fases do projeto

### 4.1 Fase 0 — Fundação

#### Implementado

* criação do catálogo `dbw_telcostream_dev`
* criação dos schemas `bronze`, `silver`, `gold`, `ops`, `pipeline_lab`, `security`
* criação dos volumes de landing e estado operacional
* geração do lote inicial de dados telco
* carga inicial nas tabelas Bronze

#### Objetos principais

* `bronze.bronze_cdr`
* `bronze.customer_events`
* `bronze.raw_cdr_landing`
* `bronze.raw_customer_landing`
* `ops.pipeline_state`

#### Como verificar

* `SHOW TABLES IN dbw_telcostream_dev.bronze`
* `SELECT count(*) FROM dbw_telcostream_dev.bronze.bronze_cdr`
* `SELECT count(*) FROM dbw_telcostream_dev.bronze.customer_events`

#### Validação esperada

* `bronze_cdr` carregada inicialmente
* `customer_events` carregada inicialmente
* volumes visíveis no Catalog Explorer

---

### 4.2 Fase 1 — Silver

#### Implementado

* criação da tabela `silver.cdr_silver` com schema tipado
* classificação de registros válidos e inválidos
* deduplicação por `(tenant_id, call_id)` com maior `event_version`
* `MERGE` idempotente Bronze → Silver
* criação de `silver.cdr_quarantine`

#### Lógica de negócio aplicada

* registros inválidos não entram na Silver principal
* duplicatas são consolidadas pelo critério de versão mais recente
* o processo pode ser reexecutado sem corromper o estado final

#### Como verificar

* `SELECT count(*) FROM dbw_telcostream_dev.silver.cdr_silver`
* `SELECT count(*) FROM dbw_telcostream_dev.silver.cdr_quarantine`
* comparação de `call_id` duplicados entre Bronze e Silver

#### Validação esperada

* `cdr_silver` = **1.020** linhas válidas
* `cdr_quarantine` = **4** linhas inválidas

---

### 4.3 Fase 2 — Replay do lote 02

#### Implementado

* ingestão do segundo lote com:
  * correções de registros (`v2`)
  * late arrivals
  * duplicatas
  * alterações de clientes premium
* Auto Loader para CDRs
* `COPY INTO` para clientes
* replay do `MERGE` Silver sem duplicação indevida

#### Como verificar

* recontar Bronze, Silver e Quarantine
* validar reconciliação final

#### Validação esperada

* `bronze.bronze_cdr` = **1.149**
* `bronze.customer_events` = **110**
* reconciliação: **1.149 = 1.020 + 4 + 125**

---

### 4.4 Fase 3 — SCD Tipo 2

#### Implementado

* criação da dimensão histórica `silver.dim_customer_scd2`
* colunas de vigência `valid_from`, `valid_to`, `is_current`
* fechamento e abertura de versões por mudança de plano do cliente

#### Como verificar

* `SELECT count(*) FROM dbw_telcostream_dev.silver.dim_customer_scd2`
* consultar o histórico de um cliente alterado, como `C000`

#### Validação esperada

* **110** linhas na dimensão histórica
* histórico coerente de mudança BASIC → PREMIUM
* 100 registros correntes

---

### 4.5 Fase 4 — Gold

#### Implementado

* criação da tabela `gold.kpi_tower_hourly`
* agregação por antena, hora e região
* cálculo de métricas operacionais:
  * chamadas totais
  * chamadas concluídas
  * chamadas derrubadas
  * consumo de dados
  * SMS
  * duração média

#### Como verificar

* `SELECT count(*) FROM dbw_telcostream_dev.gold.kpi_tower_hourly`
* `SELECT * FROM dbw_telcostream_dev.gold.kpi_tower_hourly LIMIT 5`

#### Validação esperada

* **72** grupos hora/antena
* aderência ao manifesto do lote 02

---

### 4.6 Fase 5 — Lakeflow Spark Declarative Pipeline

#### Implementado

* pipeline `telcostream_sdp`
* saídas no schema `pipeline_lab`
* objetos `_sdp` espelhando Bronze, Silver e Gold
* expectations declarativas para qualidade de dados

#### Objetos criados

* `pipeline_lab.bronze_cdr_sdp`
* `pipeline_lab.bronze_customers_sdp`
* `pipeline_lab.cdr_silver_sdp`
* `pipeline_lab.kpi_tower_hourly_sdp`

#### Como verificar

* Catalog Explorer → pipeline `telcostream_sdp`
* `SHOW TABLES IN dbw_telcostream_dev.pipeline_lab`
* contagens das tabelas `_sdp`

#### Validação esperada

* Bronze SDP = **1.149**
* Customers SDP = **110**
* Silver SDP = **1.020**
* Gold SDP = **72**

---

### 4.7 Fase 6 — Lakeflow Job

#### Implementado

* job `telcostream_pipeline_job`
* 3 tarefas em sequência:
  * ingestão Bronze
  * processamento Silver
  * construção Gold
* parâmetros operacionais básicos: serialização, timeout e dependências

#### Como verificar

* página de Jobs
* grafo de dependências do job
* histórico de runs

#### Validação esperada

* run `695010521785213` com sucesso
* 3 tarefas concluídas com sucesso

---

### 4.8 Fase 7 — Git e Declarative Automation Bundle

#### Implementado

* Git folder conectado ao repositório GitHub
* branch `codex/telcostream-lab`
* criação e validação do `databricks.yml`
* bind do pipeline existente ao bundle
* deploy bem-sucedido do job e do pipeline

#### Como verificar

* arquivo `databricks.yml` no repo
* `docs/decisoes.md` com decisão sobre `schema` vs `target`
* página do job do bundle e página do pipeline

#### Validação esperada

* `bundle validate --target dev` bem-sucedido
* `bundle deploy --target dev` bem-sucedido
* job do bundle criado: `742363202625953`

---

### 4.9 Fase 8 — Governança e segurança

#### Implementado

* função `security.mask_pii`
* máscaras de coluna em `msisdn` e `document_id`
* função `security.row_filter_tenant`
* row filter em `tenant_id`
* GRANTs para consumo de Gold

#### Limitação conhecida

O item de grupos UC ficou parcialmente adaptado porque a conta usada no lab não está provisionada no tenant corporativo do Account Console. Por isso, o fallback foi aplicar GRANTs ao usuário atual para demonstrar o padrão técnico.

#### Como verificar

* `DESCRIBE EXTENDED dbw_telcostream_dev.silver.cdr_silver`
* query com `is_member('telco_analysts')`
* checagem visual da aba Lineage no Catalog Explorer

#### Validação esperada

* seção `Row Filter` presente no `DESCRIBE EXTENDED`
* seção `Column Masks` presente no `DESCRIBE EXTENDED`
* owner vê PII em claro; analistas veriam dados mascarados

---

### 4.10 Fase 9 — Azure Extensions

#### Implementado

* external table de laboratório em path externo ao `__unitystorage`
* secret scope Databricks-backed `telcostream-scope`
* mini lab real com storage externo:
  * storage account `<EXTERNAL_STORAGE_ACCOUNT>`
  * Access Connector `<ACCESS_CONNECTOR_NAME>`
  * storage credential `telco_external_cred`
  * external location `telco_external_raw`
  * external table `bronze.kpi_external_real`

#### Como verificar

* `SHOW STORAGE CREDENTIALS`
* `SHOW EXTERNAL LOCATIONS`
* `SELECT count(*) FROM dbw_telcostream_dev.bronze.kpi_external_real`
* Azure Portal no storage `<EXTERNAL_STORAGE_ACCOUNT>`

#### Validação esperada

* 2 storage credentials visíveis
* 2 external locations visíveis
* `kpi_external_real` = **72** linhas

#### Observação técnica relevante

O storage gerenciado do Databricks no managed resource group apresenta **deny assignment**, então não deve ser tratado como evidência de external storage empresarial. O mini lab corrige esse ponto usando um storage account externo real.

---

### 4.11 Fase 10 — Evidências e documentação

#### Implementado

* `README.md`
* `evidencias/00_ambiente.md`
* `docs/decisoes.md`
* roteiro de demonstração de 8 minutos
* células de evidência no notebook checklist

#### Como verificar

* abrir o repositório Git e os arquivos de documentação
* abrir o notebook checklist com as cells de evidência

#### Validação esperada

* documentação alinhada ao estado real do workspace
* saídas verificadas e reproduzíveis

---

## 5. Matriz final de validação

| Evidência | Resultado esperado | Status |
| --- | --- | --- |
| `bronze.bronze_cdr` | 1.149 | ✅ |
| `bronze.customer_events` | 110 | ✅ |
| `silver.cdr_silver` | 1.020 | ✅ |
| `silver.cdr_quarantine` | 4 | ✅ |
| `silver.dim_customer_scd2` | 110 | ✅ |
| `gold.kpi_tower_hourly` | 72 | ✅ |
| `pipeline_lab.bronze_cdr_sdp` | 1.149 | ✅ |
| `pipeline_lab.bronze_customers_sdp` | 110 | ✅ |
| `pipeline_lab.cdr_silver_sdp` | 1.020 | ✅ |
| `pipeline_lab.kpi_tower_hourly_sdp` | 72 | ✅ |
| `bronze.kpi_external_snapshot` | 72 | ✅ |
| `bronze.kpi_external_real` | 72 | ✅ |
| `SHOW STORAGE CREDENTIALS` | 2 credentials | ✅ |
| `SHOW EXTERNAL LOCATIONS` | 2 locations | ✅ |
| `DESCRIBE EXTENDED cdr_silver` | row filter + column masks | ✅ |
| `telcostream_pipeline_job` | run com sucesso | ✅ |
| `telcostream_sdp` | pipeline idle e válido | ✅ |

---

## 6. Decisões técnicas mais importantes

Os principais pontos de engenharia adotados no projeto foram:

* `MERGE` com **CTE inline** para evitar dependência de TEMP VIEW entre statements
* `TRY_CAST` para tratar dados inválidos sem abortar a carga
* lógica idempotente baseada em `event_version`
* uso de `delta.feature.allowColumnDefaults` na tabela SCD2
* correção de `target` para `schema` no bundle do pipeline
* segregação do SDP em `pipeline_lab`
* uso de secret scope Databricks-backed em ambiente de lab
* uso de storage externo real para demonstrar external location corretamente

Para o racional detalhado de cada decisão, consultar `docs/decisoes.md`.

---

## 7. Como este projeto se conecta à DP-750

O projeto cobre de forma prática vários blocos que costumam ser avaliados em uma trilha de engenharia de dados em Databricks:

### 7.1 Data ingestion

* Auto Loader
* `COPY INTO`
* ingestão incremental
* idempotência

### 7.2 Data transformation

* MERGE
* cleansing
* quarentena
* deduplicação por versão
* agregações Gold

### 7.3 Data modeling

* Medallion Architecture
* SCD Tipo 2
* tabelas gerenciadas e externas

### 7.4 Governance

* Unity Catalog
* storage credentials
* external locations
* column masks
* row filters
* grants

### 7.5 Orchestration and deployment

* Lakeflow Jobs
* Lakeflow Spark Declarative Pipelines
* Git integration
* Declarative Automation Bundle

### 7.6 Troubleshooting and validation

* leitura de erros de SQL/REST
* correção de sintaxe e semântica
* validação com contagens e evidências reproduzíveis

---

## 8. Pontos fortes para uma entrevista técnica

### 8.1 Pontos que demonstram maturidade técnica

* não apenas construiu a pipeline, mas **validou cada fase com evidência objetiva**
* tratou problemas reais de plataforma e sintaxe
* implementou governança de dados no nível de metastore, não só em lógica de aplicação
* integrou Databricks com Azure externo de forma alinhada ao padrão corporativo
* documentou decisões técnicas e limitações de ambiente com clareza

### 8.2 Narrativa recomendada

Uma boa narrativa para uma apresentação técnica é:

1. explicar o caso de uso telco e a arquitetura Medallion
2. mostrar as contagens e o manifesto de reconciliação
3. destacar o SCD2 e o tratamento de qualidade de dados
4. mostrar o job e o pipeline declarativo
5. mostrar governança com `DESCRIBE EXTENDED`
6. fechar com o contraste entre managed storage e external storage real no Azure

### 8.3 Perguntas prováveis

* por que usar Auto Loader em vez de leitura simples de arquivo?
* por que a Silver usa MERGE e não append simples?
* como garantir replay sem duplicidade?
* quando usar tabela gerenciada vs tabela externa?
* por que o storage do managed resource group não serve como external location de produção?
* como o row filter e a mask são aplicados pelo Unity Catalog?
* qual a diferença entre job, pipeline declarativo e bundle?

---

## 9. Considerações de custo

Como o ambiente usa uma conta de teste com orçamento limitado, o projeto foi analisado sob ótica de custo.

### Observações práticas

* o custo relevante veio do período de desenvolvimento e reexecução de pipelines/jobs
* no estado final, o ambiente ficou essencialmente **idle**:
  * SQL warehouse parado
  * pipeline em `IDLE`
  * sem clusters clássicos ativos
* o mini lab Azure deve ser removido após a captura de evidências se o objetivo for apenas demonstração

### Recomendações

* evitar reruns completos de pipeline/job sem necessidade
* usar screenshots e documentação já gerada para revisão
* manter auto-stop agressivo em warehouses
* apagar recursos Azure externos quando não forem mais necessários

---

## 10. Roteiro resumido de verificação final

Para uma revisão técnica rápida, a sequência recomendada é:

1. abrir o notebook checklist
2. rodar a evidência de contagens end-to-end
3. rodar a evidência de governança ativa
4. rodar `DESCRIBE EXTENDED cdr_silver`
5. rodar `SHOW EXTERNAL LOCATIONS`
6. rodar `SHOW STORAGE CREDENTIALS`
7. abrir o Azure Portal e mostrar:
   * `<EXTERNAL_STORAGE_ACCOUNT>` acessível
   * storage gerenciado do Databricks com erro 403

---

## 11. Conclusão

O projeto TelcoStream Lakehouse foi concluído com sucesso como um laboratório técnico completo, cobrindo ingestão, transformação, modelagem, governança, automação, external data access e documentação.

Mais importante que o volume de objetos criados foi a qualidade da validação:

* todas as fases principais foram verificadas com métricas objetivas
* a governança foi comprovada no metastore
* a camada Azure externa foi demonstrada com storage real fora do managed resource group
* a documentação ficou adequada tanto para revisão de certificação quanto para apresentação em entrevista técnica

Em resumo, este projeto já funciona como:

* portfólio técnico de engenharia de dados em Databricks
* base prática para revisão de tópicos da DP-750
* narrativa robusta para entrevistas, apresentações e avaliações técnicas
