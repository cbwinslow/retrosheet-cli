
from dataclasses import dataclass
from pathlib import Path

@dataclass
class RetrosheetConfig:
    base_url: str = "https://www.retrosheet.org"
    downloads_base: str = "https://www.retrosheet.org/downloads"
    data_dir: Path = Path("data/retrosheet")
    # 7 master CSVs zip that covers all games 1898-2025
    main_csv_zip: str = "https://www.retrosheet.org/downloads/retrosheet-csv.zip"  # actual URL should be kept in sync with site
    # parsed play-by-play master file
    plays_all_zip: str = "https://www.retrosheet.org/downloads/plays-all.zip"  # see plays.html

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "staging").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "warehouse").mkdir(parents=True, exist_ok=True)
