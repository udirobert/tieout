-- close-keeper federation sources for the Open Agent Hackathon wildcard demo.
-- Three genuinely separate sources, one Lightning SQL surface:
--   bank_feed            the bank statement staging lines (close-tieout-bank-cp)
--   corvus_le_reference  the legal-entity reference master (close-tieout-le-map)
--   gl_movements         the GL movement lines (close-tieout-movements-rec)
--
-- Register the logical database first, then one FILESTORE table per CSV.
-- CSVs come from scripts/export_close_sources.py; copy them to the Zetaris
-- host and fix PATH to wherever they land (the compose bundle can mount a
-- host dir into the driver container, or use an s3a:// path).

CREATE LIGHTNING DATABASE close_federation
DESCRIBE BY "close-keeper federated close package (bank feed, LE reference, GL)";

CREATE LIGHTNING FILESTORE TABLE bank_feed
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/data/close-sources/bank_feed.csv",
  inferSchema "true",
  header "true"
);

CREATE LIGHTNING FILESTORE TABLE corvus_le_reference
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/data/close-sources/corvus_le_reference.csv",
  inferSchema "true",
  header "true"
);

CREATE LIGHTNING FILESTORE TABLE gl_movements
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/data/close-sources/gl_movements.csv",
  inferSchema "true",
  header "true"
);
