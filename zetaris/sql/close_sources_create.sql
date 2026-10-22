-- close-keeper federation sources for the Open Agent Hackathon wildcard demo.
-- Three genuinely separate sources, one Lightning SQL surface:
--   bank_feed            the bank statement staging lines (close-tieout-bank-cp)
--   corvus_le_reference  the legal-entity reference master (close-tieout-le-map)
--   gl_movements         the GL movement lines (close-tieout-movements-rec)
--
-- Register the logical database first, then one FILESTORE table per CSV.
-- CSVs come from scripts/export_close_sources.py; staged 22 Oct into the
-- driver container's customer-data volume at the PATHs below (docker cp —
-- the bundle already mounts customer-data at /home/zetaris/customer-data,
-- so no compose change or restart is needed).

CREATE LIGHTNING DATABASE close_federation
DESCRIBE BY "close-keeper federated close package (bank feed, LE reference, GL)";

CREATE LIGHTNING FILESTORE TABLE bank_feed
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/home/zetaris/customer-data/close-sources/bank_feed.csv",
  inferSchema "true",
  header "true"
);

CREATE LIGHTNING FILESTORE TABLE corvus_le_reference
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/home/zetaris/customer-data/close-sources/corvus_le_reference.csv",
  inferSchema "true",
  header "true"
);

CREATE LIGHTNING FILESTORE TABLE gl_movements
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "/home/zetaris/customer-data/close-sources/gl_movements.csv",
  inferSchema "true",
  header "true"
);
