
import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests
import psycopg2
from psycopg2.extras import execute_batch

from config import RetrosheetConfig


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
            total_size = int(r.headers.get("content-length", 0))
            with open(dest, "wb") as f:
                with tqdm(total=total_size, unit="B", unit_scale=True, desc=dest.name) as pbar:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        return dest

    def download_retro_csv_zip(self) -> Path:
        dest = self.cfg.data_dir / "raw" / "retrocsv.zip"
        if dest.exists():
            logger.info("Retro CSV zip already exists, skipping download: %s", dest)
            return dest
        return self._download(self.cfg.retro_csv_zip, dest)

    def download_support_zips(self) -> list[Path]:
        urls = {
            "biofile": self.cfg.biofile_zip,
            "negroleagues": self.cfg.negro_leagues_zip,
            "postseason": self.cfg.postseason_zip,
            "allstar": self.cfg.allstar_zip,
            "federal": self.cfg.federal_zip,
            "tiebreakers": self.cfg.tiebreakers_zip,
            "gamelogs": self.cfg.gamelogs_zip,
            "transactions": self.cfg.transactions_zip,
            "schedules": self.cfg.schedules_zip,
            "rosters": self.cfg.rosters_zip,
            "ejections_standalone": self.cfg.ejections_zip,
        }
        # Add special milestone zips
        for key, url in self.cfg.special_zips.items():
            urls[f"special_{key}"] = url

        paths = []
        logger.info("Starting bulk download of %d support archives...", len(urls))
        for name, url in tqdm(urls.items(), desc="Archives"):
            dest = self.cfg.data_dir / "raw" / f"{name}.zip"
            if not dest.exists():
                try:
                    paths.append(self._download(url, dest))
                except Exception as e:
                    logger.error("Failed to download %s (%s): %s", name, url, e)
            else:
                logger.info("%s zip already exists, skipping: %s", name, dest)
                paths.append(dest)
        return paths

    def download_all(self) -> list[Path]:
        all_zips = [self.download_retro_csv_zip()]
        all_zips.extend(self.download_support_zips())
        return all_zips

    def extract_zip(self, zip_path: Path, dest_dir: Optional[Path] = None) -> Path:
        if dest_dir is None:
            dest_dir = self.cfg.data_dir / "staging" / zip_path.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = zf.namelist()
            logger.info("Extracting %s (%d files) -> %s", zip_path.name, len(file_list), dest_dir)
            for member in tqdm(file_list, desc=f"Extracting {zip_path.name}", leave=False):
                zf.extract(member, dest_dir)
        return dest_dir


class RetrosheetIngestor:
    def __init__(self, pg_cfg: PostgresConnectionConfig, rs_cfg: RetrosheetConfig) -> None:
        self.pg_cfg = pg_cfg
        self.rs_cfg = rs_cfg

    def _conn(self):
        return psycopg2.connect(self.pg_cfg.dsn)

    def init_schema(self) -> None:
        ddl_path = Path(__file__).parent / "ddl_postgres.sql"
        logger.info("Initializing schema from %s", ddl_path)
        with self._conn() as conn:
            with conn.cursor() as cur:
                with open(ddl_path, "r") as f:
                    cur.execute(f.read())

    def _copy_csv(self, cursor, table: str, csv_path: Path, header: bool = True, delimiter: str = ",") -> None:
        logger.info("COPY %s FROM %s", table, csv_path)
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            if header:
                try:
                    next(f)
                except StopIteration:
                    logger.warning("File %s is empty, skipping.", csv_path)
                    return
            # Use copy_expert with appropriate options
            copy_sql = f"COPY {table} FROM STDIN WITH (FORMAT csv, DELIMITER '{delimiter}', ENCODING 'UTF8', QUOTE '\"')"
            cursor.copy_expert(copy_sql, f)

    def ingest_master_csvs(self) -> None:
        staging_root = self.rs_cfg.data_dir / "staging"
        
        # Comprehensive list of categories that provide the standard 7-8 CSVs
        sources = [
            "retrocsv", "negroleagues", "allngldata", "postseason", 
            "allstar", "federal", "tiebreakers"
        ]
        
        mapping = {
            "allplayers.csv": "retrosheet.allplayers",
            "gameinfo.csv": "retrosheet.gameinfo",
            "teamstats.csv": "retrosheet.teamstats",
            "batting.csv": "retrosheet.batting",
            "pitching.csv": "retrosheet.pitching",
            "fielding.csv": "retrosheet.fielding",
            "plays.csv": "retrosheet.plays_raw",
            "ejections.csv": "retrosheet.ejections",
        }

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica';")
                for src in sources:
                    staging_dir = staging_root / src
                    if not staging_dir.exists():
                        continue
                    
                    for filename, table in mapping.items():
                        # Robust recursive find
                        paths = [p for p in staging_dir.rglob("*") if p.name.lower() == filename.lower()]
                        if paths:
                            self._copy_csv(cur, table, paths[0])
                cur.execute("SET session_replication_role = 'origin';")

    def ingest_gamelogs(self) -> None:
        staging_dir = self.rs_cfg.data_dir / "staging" / "gamelogs"
        if not staging_dir.exists():
            return

        with self._conn() as conn:
            with conn.cursor() as cur:
                # Game logs are .txt files, comma-delimited, NO header, and use double quotes
                for path in staging_dir.rglob("*.txt"):
                    if "GL" in path.name.upper():
                        self._copy_csv(cur, "retrosheet.gamelogs", path, header=False)

    def ingest_support_tables(self) -> None:
        staging_root = self.rs_cfg.data_dir / "staging"
        
        bio_mapping = {
            "biofile0.csv": "retrosheet.personnel",
            "ballparks0.csv": "retrosheet.parks",
            "umpires0.csv": "retrosheet.umpires",
            "managers0.csv": "retrosheet.managers",
            "coaches0.csv": "retrosheet.coaches",
            "teams0.csv": "retrosheet.teams",
        }
        
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica';")
                
                # Handle biofile/biodata
                for stem in ["biofile", "biodata"]:
                    bio_dir = staging_root / stem
                    if bio_dir.exists():
                        for filename, table in bio_mapping.items():
                            paths = [p for p in bio_dir.rglob("*") if p.name.lower() == filename.lower()]
                            if paths:
                                self._copy_csv(cur, table, paths[0])
                
                # Handle rosters
                roster_dir = staging_root / "rosters"
                if roster_dir.exists():
                    for path in roster_dir.rglob("*.ROS"):
                        # Extract season from filename (e.g. BOS2024.ROS)
                        stem = path.stem
                        season_str = "".join(filter(str.isdigit, stem))
                        if season_str:
                            season = int(season_str)
                            # ROS files are CSV-like: ID,Last,First,Bats,Throws,Team,Pos
                            # We'll use a temporary table to add the season or use a wrapper
                            cur.execute("CREATE TEMP TABLE temp_roster (player_id TEXT, last TEXT, first TEXT, bats CHAR(1), throws CHAR(1), team TEXT, pos TEXT) ON COMMIT DROP")
                            with open(path, "r", encoding="utf-8", errors="replace") as f:
                                cur.copy_expert("COPY temp_roster FROM STDIN WITH (FORMAT csv)", f)
                            cur.execute(f"INSERT INTO retrosheet.rosters SELECT *, {season} FROM temp_roster ON CONFLICT DO NOTHING")
                            cur.execute("TRUNCATE temp_roster")

                # Handle transactions
                tran_dir = staging_root / "transactions"
                if tran_dir.exists():
                    for path in tran_dir.rglob("tran.txt"):
                        self._copy_csv(cur, "retrosheet.transactions", path, header=False)
                
                # Handle schedules
                sched_dir = staging_root / "schedules"
                if sched_dir.exists():
                    for path in sched_dir.rglob("*"):
                        name_upper = path.name.upper()
                        if (".TXT" in name_upper or ".CSV" in name_upper) and \
                           ("SKED" in name_upper or "SCHEDULE" in name_upper):
                            self._copy_csv(cur, "retrosheet.schedules", path, header=False)
                
                # Handle milestones
                for key in self.rs_cfg.special_zips.keys():
                    ms_dir = staging_root / f"special_{key}"
                    if ms_dir.exists():
                        for path in ms_dir.rglob("*.csv"):
                            # Milestones often have headers
                            cur.execute(f"CREATE TEMP TABLE temp_ms (game_id TEXT, date DATE, player_id TEXT, team TEXT, opp TEXT, details TEXT) ON COMMIT DROP")
                            with open(path, "r", encoding="utf-8", errors="replace") as f:
                                # Skip header
                                next(f)
                                cur.copy_expert("COPY temp_ms FROM STDIN WITH (FORMAT csv)", f)
                            cur.execute(f"INSERT INTO retrosheet.milestones SELECT '{key}', * FROM temp_ms")
                            cur.execute("TRUNCATE temp_ms")

                cur.execute("SET session_replication_role = 'origin';")

    def vacuum_analyze(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                logger.info("Running ANALYZE on retrosheet schema")
                cur.execute("ANALYZE retrosheet")
