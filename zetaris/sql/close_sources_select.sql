-- Federation sanity checks: each source answers, then one query crosses two.

SELECT COUNT(*) AS bank_feed_rows FROM close_federation.bank_feed;
SELECT COUNT(*) AS corvus_le_rows FROM close_federation.corvus_le_reference;
SELECT COUNT(*) AS gl_movements_rows FROM close_federation.gl_movements;

-- The judgment-queue question a file per source cannot answer alone:
-- staging lines whose pulled-out sender has no legal-entity match.
SELECT account_name, narrative, pulled_out_sender_beneficiary, credit_amount, debit_amount
FROM close_federation.bank_feed
WHERE matched_legal_entity IS NULL OR matched_legal_entity = '';

-- LE mapping coverage: mapped names that exist in the reference master.
SELECT le.legal_entity, ref.corvus_le_id
FROM close_federation.gl_movements le
LEFT JOIN close_federation.corvus_le_reference ref
  ON le.legal_entity = ref.corvus_le;
