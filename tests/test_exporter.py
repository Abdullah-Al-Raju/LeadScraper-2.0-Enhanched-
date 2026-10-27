import json
import csv
import pytest
from pathlib import Path
from lead_scraper.models import Lead
from lead_scraper.exporter import export_leads


def test_export_leads(tmp_path: Path):
    leads = [
        Lead(
            business_name="Falcon Coffee",
            website="https://falconcoffee.com",
            emails=["hello@falconcoffee.com"],
            phones=["555-0100"],
            social_media={"instagram": "https://instagram.com/falconcoffee"},
            location="San Francisco",
        ),
        Lead(
            business_name="Precision Mechanics",
            website="https://precisionmech.com",
            emails=["service@precisionmech.com"],
            phones=["555-0200"],
            location="Austin, TX",
        )
    ]

    paths = export_leads(leads, output_dir=tmp_path, prefix="test_export")

    # 1. Check JSON
    json_path = paths["json"]
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 2
        assert data[0]["business_name"] == "Falcon Coffee"
        assert data[1]["business_name"] == "Precision Mechanics"

    # 2. Check CSV
    csv_path = paths["csv"]
    assert csv_path.exists()
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["business_name"] == "Falcon Coffee"
        assert reader[0]["emails"] == "hello@falconcoffee.com"

    # 3. Check TXT
    txt_path = paths["txt"]
    assert txt_path.exists()
    content = txt_path.read_text(encoding="utf-8")
    assert "FALCON COFFEE" in content
    assert "PRECISION MECHANICS" in content
