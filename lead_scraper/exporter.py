"""
Multi-Format Auto-Exporter for LeadScraper.
Automatically writes all scraped leads to JSON, CSV, and formatted TXT cards.
Requires zero configuration and displays clear output paths for users.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from lead_scraper.models import Lead
from lead_scraper.config import OUTPUT_DIR


def export_leads(
    leads: List[Lead],
    output_dir: Optional[Path] = None,
    prefix: str = "leads"
) -> Dict[str, Path]:
    """
    Saves leads automatically to JSON, CSV, and TXT in the target directory.
    Returns a dictionary of absolute file paths.
    """
    target_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"{prefix}_{timestamp}"

    json_path = target_dir / f"{base_name}.json"
    csv_path = target_dir / f"{base_name}.csv"
    txt_path = target_dir / f"{base_name}.txt"

    # 1. Export JSON
    json_data = [lead.model_dump() for lead in leads]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # 2. Export CSV (using utf-8-sig for seamless Excel opening on Windows)
    if leads:
        flat_records = [lead.to_flat_dict() for lead in leads]
        headers = list(flat_records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(flat_records)
    else:
        csv_path.touch()

    # 3. Export Human-Readable TXT
    avg_conf = (
        sum(lead.confidence_score for lead in leads) / len(leads) if leads else 0.0
    )
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("                LEADSCRAPER FALCON EXPORT               \n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated at:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Leads:        {len(leads)}\n")
        f.write(f"Average Quality:    {int(avg_conf * 100)}%\n")
        f.write("=" * 60 + "\n\n")

        for i, lead in enumerate(leads, 1):
            f.write(f"LEAD #{i}\n")
            f.write(lead.display_card() + "\n\n")

    return {
        "json": json_path.resolve(),
        "csv": csv_path.resolve(),
        "txt": txt_path.resolve(),
    }
