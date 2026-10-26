-- FX source verification + the question it exists to answer.

-- Coverage: one row per rate_date — the three value_dates in bank_feed.
SELECT * FROM close_fx.fx_rates_eur ORDER BY rate_date;

-- The load-bearing query: restate every bank staging line in GBP at its
-- value-date rate. bank_feed is a FILESTORE CSV in SeaweedFS S3;
-- fx_rates_eur is a live public REST API — one SELECT crosses both.
SELECT b.pulled_out_sender_beneficiary AS counterparty,
       b.currency,
       CAST(b.value_date AS DATE) AS value_date,
       b.debit_amount,
       ROUND(b.debit_amount * f.gbp_rate /
             CASE lower(b.currency)
               WHEN 'dkk' THEN f.dkk_rate
               WHEN 'eur' THEN f.eur_rate
               ELSE f.gbp_rate END, 2) AS gbp_amount
FROM close_federation.bank_feed b
JOIN close_fx.fx_rates_eur f
  ON CAST(b.value_date AS DATE) = CAST(f.rate_date AS DATE)
ORDER BY value_date, counterparty;
