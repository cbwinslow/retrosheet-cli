
import argparse
import logging
from pathlib import Path

from config import RetrosheetConfig
from ingest import PostgresConnectionConfig, RetrosheetDownloader, RetrosheetIngestor


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrosheet bulk downloader and ingestor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dl = sub.add_parser("download", help="Download all Retrosheet zips (CSV, bio, ejections, etc.)")
    dl.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"))

    ing = sub.add_parser("ingest", help="Ingest Retrosheet CSVs into Postgres")
    ing.add_argument("--dsn", required=True, help="PostgreSQL DSN")
    ing.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"))
    ing.add_argument("--init-schema", action="store_true", help="Initialize schema (run DDL)")

    full = sub.add_parser("full", help="Download and ingest everything (Total Mirror)")
    full.add_argument("--dsn", required=True, help="PostgreSQL DSN (e.g. postgresql://user:pass@localhost:5432/db)")
    full.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"), help="Directory for raw/staging files")

    bootstrap = sub.add_parser("bootstrap", help="Robust one-step environment setup and data ingestion")
    bootstrap.add_argument("--dsn", required=True, help="PostgreSQL DSN")
    bootstrap.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"))

    args = parser.parse_args()

    if args.cmd == "download":
        cfg = RetrosheetConfig(data_dir=args.data_dir)
        dlr = RetrosheetDownloader(cfg)
        zips = dlr.download_all()
        for z in zips:
            dlr.extract_zip(z)
    elif args.cmd == "ingest":
        rs_cfg = RetrosheetConfig(data_dir=args.data_dir)
        pg_cfg = PostgresConnectionConfig(dsn=args.dsn)
        ingestor = RetrosheetIngestor(pg_cfg, rs_cfg)
        if args.init_schema:
            ingestor.init_schema()
        ingestor.ingest_master_csvs()
        ingestor.ingest_support_tables()
        ingestor.ingest_gamelogs()
        ingestor.vacuum_analyze()
    elif args.cmd in ["full", "bootstrap"]:
        logging.info("Starting robust bootstrap of Retrosheet data...")
        cfg = RetrosheetConfig(data_dir=args.data_dir)
        dlr = RetrosheetDownloader(cfg)
        zips = dlr.download_all()
        for z in zips:
            dlr.extract_zip(z)
        
        pg_cfg = PostgresConnectionConfig(dsn=args.dsn)
        ingestor = RetrosheetIngestor(pg_cfg, cfg)
        ingestor.init_schema()
        ingestor.ingest_master_csvs()
        ingestor.ingest_support_tables()
        ingestor.ingest_gamelogs()
        ingestor.vacuum_analyze()
        logging.info("Bootstrap complete. Retrosheet database is ready.")


if __name__ == "__main__":
    main()
