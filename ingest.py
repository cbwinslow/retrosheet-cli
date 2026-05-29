
import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests
import psycopg2
from psycopg2.extras import execute_batch

from .config import RetrosheetConfig


logger = logging.getLogger(__name__)


@dataclass
class PostgresConnectionConfig:
    dsn: str  # e.g. "postgresql://user:pass@localhost:5432/baseball"


class RetrosheetDownloader:
    def __init__(self, cfg: RetrosheetConfig) -> None:
        self.cfg = cfg
        self.cfg.ensure_dirs()

    def _download(self, url: str, dest: Path, chunk_size: int = 1 << 20) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading %s -> %s", url, dest)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        return dest

    def download_main_csv_zip(self) -> Path:
        dest = self.cfg.data_dir / "raw" / "retrosheet-main-csv.zip"
        if dest.exists():
            logger.info("Main CSV zip already exists, skipping download: %s", dest)
            return dest
        return self._download(self.cfg.main_csv_zip, dest)

    def download_plays_all_zip(self) -> Path:
        dest = self.cfg.data_dir / "raw" / "retrosheet-plays-all.zip"
        if dest.exists():
            logger.info("plays-all zip already exists, skipping download: %s", dest)
            return dest
        return self._download(self.cfg.plays_all_zip, dest)

    def extract_zip(self, zip_path: Path, dest_dir: Optional[Path] = None) -> Path:
        if dest_dir is None:
            dest_dir = self.cfg.data_dir / "staging"
        dest_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Extracting %s -> %s", zip_path, dest_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        return dest_dir


class RetrosheetIngestor:
    def __init__(self, pg_cfg: PostgresConnectionConfig, rs_cfg: RetrosheetConfig) -> None:
        self.pg_cfg = pg_cfg
        self.rs_cfg = rs_cfg

    def _conn(self):
        return psycopg2.connect(self.pg_cfg.dsn)

    def _copy_csv(self, cursor, table: str, csv_path: Path, header: bool = True) -> None:
        logger.info("COPY %s FROM %s", table, csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            if header:
                # psycopg2 COPY can't skip header directly; use io wrapper
                next(f)
            cursor.copy_expert(f"COPY {table} FROM STDIN WITH (FORMAT csv)", f)

    def ingest_master_csvs(self, staging_dir: Optional[Path] = None) -> None:
        if staging_dir is None:
            staging_dir = self.rs_cfg.data_dir / "staging"

        mapping = {
            "allplayers.csv": "retrosheet.allplayers",
            "gameinfo.csv": "retrosheet.gameinfo",
            "teamstats.csv": "retrosheet.teamstats",
            "batting.csv": "retrosheet.batting",
            "pitching.csv": "retrosheet.pitching",
            "fielding.csv": "retrosheet.fielding",
            "plays.csv": "retrosheet.plays_raw",
        }

        with self._conn() as conn:
            with conn.cursor() as cur:
                for filename, table in mapping.items():
                    path = staging_dir / filename
                    if not path.exists():
                        logger.warning("File not found, skipping: %s", path)
                        continue
                    self._copy_csv(cur, table, path)

    def vacuum_analyze(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                logger.info("Running ANALYZE on retrosheet schema")
                cur.execute("ANALYZE retrosheet")
