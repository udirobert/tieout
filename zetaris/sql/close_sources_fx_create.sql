-- Fourth close-keeper federation source: live FX rates over REST.
-- bank_feed is DKK + EUR against a GBP reporting currency, so restating the
-- staging lines at the value-date rate is a real close step — and one a
-- file-per-source export cannot answer: the rates live outside the package.
--
-- Source: @fawazahmed0/currency-api on jsDelivr — date-indexed ECB-derived
-- rates, no key, effectively no rate limit at this size. One REST table per
-- value_date present in bank_feed (the endpoint is baked into the
-- registration), cached immediately so later queries don't re-call the API.
-- Pattern per zetaris/getting-started open_data/rest_apis (REST TABLE +
-- CACHE TABLE + SCHEMASTORE VIEW).
--
-- Note on flattening: the `eur` response object is a dynamic-key map, but a
-- SCHEMASTORE VIEW containing LATERAL VIEW explode() hits a Spark view +
-- Generate attribute-resolution bug (MISSING_ATTRIBUTES at query time).
-- The verified-working form is the narrow dot-access projection below —
-- the feed only needs GBP/DKK/EUR legs anyway.
--
-- Run as an operator action (one statement per call, no trailing semicolons)
-- through /api/proxy/sql-editor/sqls/run — the agent's query_close_source
-- stays read-only by construction and must never run this file.

CREATE LIGHTNING DATABASE FX_RATES
DESCRIBE BY "close-keeper.federated_close_package.fx_rates";

CREATE SCHEMASTORE CONTAINER close_fx;

CREATE LIGHTNING REST TABLE eur_fx_2026_03_24 FROM FX_RATES REQUEST(
    endpoint "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-03-24/v1/currencies/eur.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
) BODY ();
CACHE TABLE fx_rates.eur_fx_2026_03_24;

CREATE LIGHTNING REST TABLE eur_fx_2026_03_25 FROM FX_RATES REQUEST(
    endpoint "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-03-25/v1/currencies/eur.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
) BODY ();
CACHE TABLE fx_rates.eur_fx_2026_03_25;

CREATE LIGHTNING REST TABLE eur_fx_2026_03_31 FROM FX_RATES REQUEST(
    endpoint "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-03-31/v1/currencies/eur.json",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER (
) BODY ();
CACHE TABLE fx_rates.eur_fx_2026_03_31;

CREATE SCHEMASTORE VIEW fx_rates_eur WITH CONTAINER close_fx AS
SELECT date AS rate_date, eur.gbp AS gbp_rate, eur.dkk AS dkk_rate, eur.eur AS eur_rate
FROM fx_rates.eur_fx_2026_03_24
UNION ALL
SELECT date AS rate_date, eur.gbp AS gbp_rate, eur.dkk AS dkk_rate, eur.eur AS eur_rate
FROM fx_rates.eur_fx_2026_03_25
UNION ALL
SELECT date AS rate_date, eur.gbp AS gbp_rate, eur.dkk AS dkk_rate, eur.eur AS eur_rate
FROM fx_rates.eur_fx_2026_03_31;
