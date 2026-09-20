-- =============================================================
-- TelcoStream Lakehouse — Fase 8: Governança e Segurança
-- Catálogo: dbw_telcostream_dev
-- =============================================================

-- ---------------------------------------------------------------
-- 8.1  GRANTs — acesso de leitura na Gold para analistas
-- Nota: requer grupo de conta criado no Account Console.
--       Em dev/lab, aplique diretamente ao usuário se necessário.
-- ---------------------------------------------------------------
GRANT USE CATALOG ON CATALOG dbw_telcostream_dev TO `telco_analysts`;
GRANT USE SCHEMA  ON SCHEMA  dbw_telcostream_dev.gold TO `telco_analysts`;
GRANT SELECT      ON TABLE   dbw_telcostream_dev.gold.kpi_tower_hourly TO `telco_analysts`;
-- Silver negada por omissão (UC nega tudo que não foi concedido)

-- ---------------------------------------------------------------
-- 8.2  Column Mask — ocultar PII de msisdn e document_id
--      is_member('telco_analysts') = true  → dado mascarado
--      is_member('telco_analysts') = false → valor real (admins)
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION dbw_telcostream_dev.security.mask_pii(value STRING)
RETURNS STRING
COMMENT 'Oculta PII para usuários sem privilégio'
RETURN
  CASE
    WHEN is_member('telco_analysts') THEN regexp_replace(value, '.', '*')
    ELSE value
  END;

ALTER TABLE dbw_telcostream_dev.silver.cdr_silver
  ALTER COLUMN msisdn      SET MASK dbw_telcostream_dev.security.mask_pii;

ALTER TABLE dbw_telcostream_dev.silver.cdr_silver
  ALTER COLUMN document_id SET MASK dbw_telcostream_dev.security.mask_pii;

-- ---------------------------------------------------------------
-- 8.3  Row Filter — restringir linhas por tenant_id
--      Analistas vêem apenas tenant 'TELCO_LAB'; admins veem tudo
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION dbw_telcostream_dev.security.row_filter_tenant(
  tenant_id STRING
)
RETURNS BOOLEAN
COMMENT 'Row filter: restringe cdr_silver por tenant_id para membros de telco_analysts'
RETURN
  CASE
    WHEN is_member('telco_analysts') THEN tenant_id = 'TELCO_LAB'
    ELSE true
  END;

ALTER TABLE dbw_telcostream_dev.silver.cdr_silver
  SET ROW FILTER dbw_telcostream_dev.security.row_filter_tenant ON (tenant_id);

-- ---------------------------------------------------------------
-- 8.4  Validações
-- ---------------------------------------------------------------
-- Funções criadas no schema security:
SELECT routine_name, routine_type
FROM dbw_telcostream_dev.information_schema.routines
WHERE routine_schema = 'security'
ORDER BY routine_name;

-- Masks e row filter aplicados (seção # Column Masks + Row Filter no fundo):
DESCRIBE EXTENDED dbw_telcostream_dev.silver.cdr_silver;

-- Admin vê valores reais (is_member=false):
SELECT
  current_user()              AS usuario,
  is_member('telco_analysts') AS eh_analista,
  msisdn,
  document_id
FROM dbw_telcostream_dev.silver.cdr_silver
LIMIT 3;
