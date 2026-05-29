# AI Agent Guide: Retrosheet CLI

This document provides a map of the codebase and instructions for AI agents on how to navigate, modify, and extend the Retrosheet CLI tool.

## Directory Structure

- `/` (Root): Main entry point and configuration.
- `/data/retrosheet`: Root directory for all downloaded and processed data.
  - `/raw`: Stores original ZIP archives downloaded from Retrosheet.org.
  - `/staging`: Stores extracted CSV/TXT files before ingestion.
  - `/warehouse`: Reserved for any post-ingestion data artifacts.

## Key Files & Responsibilities

### `cli.py`
- **Purpose**: Main CLI interface using `argparse`.
- **Logic**: Orchestrates the high-level workflow (download -> extract -> initialize -> ingest).
- **Instructions**:
  - To add a new command, add a subparser to `main()`.
  - To modify the bootstrap sequence, update the `elif args.cmd in ["full", "bootstrap"]:` block.

### `config.py`
- **Purpose**: Centralized configuration and URL registry.
- **Logic**: Defines the `RetrosheetConfig` dataclass with all official download URLs.
- **Instructions**:
  - To add a new Retrosheet data source, add its URL to the class.
  - To update a URL (e.g., for a new season), modify the string literal in this file.

### `ingest.py`
- **Purpose**: Core engine for data acquisition and database loading.
- **Logic**:
  - `RetrosheetDownloader`: Handles HTTP requests and local storage. Uses `tqdm` for progress bars.
  - `RetrosheetIngestor`: Handles PostgreSQL connection, schema initialization, and bulk `COPY` operations.
- **Instructions**:
  - **Adding Data Ingestion**:
    - For a standard 8-file CSV set (like Negro Leagues): Add the archive name to `sources` in `ingest_master_csvs()`.
    - For specialized tables: Create a new method or add logic to `ingest_support_tables()`.
    - For new file formats: Update `_copy_csv()` or create a specific wrapper.

### `ddl_postgres.sql`
- **Purpose**: Database schema definition.
- **Logic**: Standard SQL with descriptive `COMMENT` statements.
- **Instructions**:
  - When adding a new table, ensure it follows the Retrosheet column headers exactly.
  - Always include `COMMENT ON TABLE` and `COMMENT ON COLUMN` for any new additions to maintain the self-documenting nature of the DB.

## Common Task Workflows

### "I want to add a new historical league"
1. Identify the ZIP URL on Retrosheet.org.
2. Add the URL to `config.py`.
3. Add the archive name to the `urls` dict in `RetrosheetDownloader.download_support_zips()`.
4. Add the archive name to the `sources` list in `RetrosheetIngestor.ingest_master_csvs()`.

### "I want to modify the Game Log schema"
1. Update the `retrosheet.gamelogs` table definition in `ddl_postgres.sql`.
2. Ensure the order of columns matches the 161-field Retrosheet specification.
3. Update the `COMMENT` statements to reflect any changes.

## Engineering Standards
- **Surgical Edits**: Prefer `replace` tool for precise updates.
- **Robustness**: Always use `session_replication_role = 'replica'` during ingestion to bypass FK checks for speed and reliability.
- **Documentation**: Keep `README` and `AGENTS.md` synchronized with any architectural changes.
