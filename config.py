from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class RetrosheetConfig:
    base_url: str = "https://www.retrosheet.org"
    data_dir: Path = Path("data/retrosheet")
    
    # Primary Aggregate Archives (Parsed CSVs)
    # Main CSV Download (1898-2025)
    retro_csv_zip: str = "https://www.retrosheet.org/downloads/csvdownloads.zip"
    # Biographical Files
    biofile_zip: str = "https://www.retrosheet.org/downloads/biodata.zip"
    # Complete Game Logs (1871-2025)
    gamelogs_zip: str = "https://www.retrosheet.org/gamelogs/gl1871_2025.zip"
    # Transactions
    transactions_zip: str = "https://www.retrosheet.org/transactions/tranDB.zip"
    # Schedules
    schedules_zip: str = "https://www.retrosheet.org/schedule/schedule.zip"
    
    # Category-specific Aggregates
    negro_leagues_zip: str = "https://www.retrosheet.org/downloads/negroleagues.zip"
    all_ngl_data_zip: str = "https://www.retrosheet.org/downloads/allngldata.zip"
    postseason_zip: str = "https://www.retrosheet.org/downloads/postseason.zip"
    allstar_zip: str = "https://www.retrosheet.org/downloads/allstar.zip"
    federal_zip: str = "https://www.retrosheet.org/downloads/federal.zip"
    tiebreakers_zip: str = "https://www.retrosheet.org/downloads/tiebreakers.zip"
    
    # Event & Box Score Aggregate Files (Raw/Semi-parsed)
    # Negro League Events/Boxes
    ngl_events_zip: str = "https://www.retrosheet.org/events/allevr.zip"
    ngl_boxes_zip: str = "https://www.retrosheet.org/events/allebr.zip"
    # All-Star & Post-Season Events
    as_events_zip: str = "https://www.retrosheet.org/events/allas.zip"
    post_events_zip: str = "https://www.retrosheet.org/events/allpost.zip"
    
    # Support & Specialized Lists
    rosters_zip: str = "https://www.retrosheet.org/rosters.zip"
    ejections_zip: str = "https://www.retrosheet.org/ejections.zip"
    
    # Milestone/Special Feature Lists
    special_zips: dict[str, str] = field(default_factory=lambda: {
        "3hr": "https://www.retrosheet.org/downloads/3HR.zip",
        "15k": "https://www.retrosheet.org/downloads/15K.zip",
        "20inn": "https://www.retrosheet.org/downloads/20innings.zip",
        "cycles": "https://www.retrosheet.org/downloads/cycles.zip",
        "interracial": "https://www.retrosheet.org/downloads/interracial.zip",
        "nohitters": "https://www.retrosheet.org/downloads/nohitters.zip",
        "tripleplays": "https://www.retrosheet.org/downloads/tripleplays.zip",
    })

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "raw").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "staging").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "warehouse").mkdir(parents=True, exist_ok=True)
