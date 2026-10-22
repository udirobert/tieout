-- close-keeper federation sources for the Open Agent Hackathon wildcard demo.
-- Three genuinely separate sources, one Lightning SQL surface:
--   bank_feed            the bank statement staging lines (close-tieout-bank-cp)
--   corvus_le_reference  the legal-entity reference master (close-tieout-le-map)
--   gl_movements         the GL movement lines (close-tieout-movements-rec)
--
-- Register the logical database first, then one FILESTORE table per CSV.
-- CSVs come from scripts/export_close_sources.py. FILESTORE rejects
-- local/container paths (bare paths and file:// both 400 "Invalid file path
-- to access") — only cloud-storage URIs register. A SeaweedFS container
-- (seaweed-s3, anonymous S3 on :9000, filer on host loopback :18888 for
-- uploads, nothing public) sits on the zetaris_default network and holds
-- the close-sources bucket. isS3BucketPublic keeps credentials out of this
-- file.

CREATE LIGHTNING DATABASE close_federation
DESCRIBE BY "close-keeper.federated_close_package.bank_feed,corvus_le_reference,gl_movements";

CREATE LIGHTNING FILESTORE TABLE bank_feed
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "s3a://close-sources/bank_feed.csv",
  inferSchema "true",
  header "true",
  isS3BucketPublic "true",
  useS3PathStyleAccess "true",
  s3Endpoint "http://seaweed-s3:9000"
);

CREATE LIGHTNING FILESTORE TABLE corvus_le_reference
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "s3a://close-sources/corvus_le_reference.csv",
  inferSchema "true",
  header "true",
  isS3BucketPublic "true",
  useS3PathStyleAccess "true",
  s3Endpoint "http://seaweed-s3:9000"
);

CREATE LIGHTNING FILESTORE TABLE gl_movements
FROM close_federation
FORMAT CSV
OPTIONS (
  PATH "s3a://close-sources/gl_movements.csv",
  inferSchema "true",
  header "true",
  isS3BucketPublic "true",
  useS3PathStyleAccess "true",
  s3Endpoint "http://seaweed-s3:9000"
);
