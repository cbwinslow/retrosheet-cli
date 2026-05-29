
import argparse
import logging
from pathlib import Path

from .config import RetrosheetConfig
from .ingest import PostgresConnectionConfig, RetrosheetDownloader, RetrosheetIngestor


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrosheet bulk downloader and ingestor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dl = sub.add_parser("download", help="Download Retrosheet master CSVs and plays")
    dl.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"))

    ing = sub.add_parser("ingest", help="Ingest Retrosheet CSVs into Postgres")
    ing.add_argument("--dsn", required=True, help="PostgreSQL DSN")
    ing.add_argument("--data-dir", type=Path, default=Path("data/retrosheet"))

    args = parser.parse_args()

    if args.cmd == "download":
        cfg = RetrosheetConfig(data_dir=args.data_dir)
        dlr = RetrosheetDownloader(cfg)
        main_zip = dlr.download_main_csv_zip()
        dlr.extract_zip(main_zip)
        plays_zip = dlr.download_plays_all_zip()
        dlr.extract_zip(plays_zip)
    elif args.cmd == "ingest":
        rs_cfg = RetrosheetConfig(data_dir=args.data_dir)
        pg_cfg = PostgresConnectionConfig(dsn=args.dsn)
        ingestor = RetrosheetIngestor(pg_cfg, rs_cfg)
        ingestor.ingest_master_csvs()
        ingestor.vacuum_analyze()


if __name__ == "__main__":
    main()
