# GEO Notes

Use official GEO programmatic access and stable GEO FTP path rules.

## Discovery

- Query GEO metadata programmatically through NCBI E-utilities.
- Treat metadata discovery separately from file download.
- Support accession-driven workflows for `GSE`, `GSM`, `GPL`, and `GDS` where the accession resolves cleanly.

## File Planning

For `GSE` accessions, plan around:

- `soft/<GSE>_family.soft.gz`
- `miniml/<GSE>_family.xml.tgz`
- `matrix/`
- `suppl/`

Use the canonical GEO bucket rule:

- `GSE12345` lives under `GSE12nnn/GSE12345`
- `GSM123456` lives under `GSM123nnn/GSM123456`

## Fetch Policy

- `metadata` scope means metadata artifacts such as SOFT and MINiML.
- `processed` scope means metadata plus matrix and supplementary files.
- `all-public` may use the same GEO public directories as `processed` in v1.
- Do not depend on brittle HTML scraping for directory enumeration.
