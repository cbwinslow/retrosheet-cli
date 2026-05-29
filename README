
# Retrosheet Bulk Ingestion

This package provides scripts and DDL to download and ingest the full set of Retrosheet
CSV outputs (allplayers, gameinfo, teamstats, batting, pitching, fielding, plays) into
PostgreSQL.

## High-level design

- Use Retrosheet's main CSV zip, which contains seven master files covering all games
  from 1898-2025.[web:1][web:14]
- Use the parsed play-by-play master `plays.csv`, which mirrors the event-file data model
  and exposes rich pitch-, plate appearance-, and baserunner-level features.[web:5][web:23]
- Land raw zips and CSVs under `data/retrosheet/raw` and `data/retrosheet/staging`.
- Ingest into a normalized `retrosheet` schema using `COPY` for bulk load.

## Usage

```bash
# 1) Download all master CSVs + plays
python -m retrosheet_ingest.cli download --data-dir data/retrosheet

# 2) Create schema
psql "$DSN" -f retrosheet_ingest/ddl_postgres.sql

# 3) Ingest into Postgres
python -m retrosheet_ingest.cli ingest --dsn "$DSN" --data-dir data/retrosheet
```

Retrosheet data copyright notice must be preserved in any derivative products:

> The information used here was obtained free of charge from and is copyrighted by
> Retrosheet. Interested parties may contact Retrosheet at 20 Sunset Rd., Newark, DE 19711.[web:1][web:5]
