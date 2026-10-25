"""
Unit tests for modules/local_exporter.py
"""

import os
import json
import csv
import pytest
from modules.local_exporter import export_to_csv, export_to_json, print_lead_summary


def test_export_to_csv_and_json(tmp_path):
    leads = [
        {
            "business_name": "Test Bakery",
            "phone_numbers": "555-111-2222",
            "email_addresses": "bread@testbakery.com",
            "website": "https://testbakery.com",
            "street_address": "12 Baker St",
            "city": "London",
            "state": None,
            "zip_code": None,
            "facebook": "https://facebook.com/testbakery",
            "instagram": "https://instagram.com/testbakery",
            "twitter": None,
            "linkedin": None,
            "youtube": None,
            "tiktok": None,
            "whatsapp": "+445551112222",
            "confidence_score": 85,
            "sources_used": "website, search_snippet"
        }
    ]

    csv_file = str(tmp_path / "leads.csv")
    json_file = str(tmp_path / "leads.json")

    # Test CSV
    export_to_csv(leads, csv_file)
    assert os.path.exists(csv_file)
    with open(csv_file, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["business_name"] == "Test Bakery"
        assert reader[0]["email_addresses"] == "bread@testbakery.com"
        assert reader[0]["whatsapp"] == "+445551112222"

    # Test JSON
    export_to_json(leads, json_file)
    assert os.path.exists(json_file)
    with open(json_file, mode="r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["business_name"] == "Test Bakery"
        assert data[0]["confidence_score"] == 85

    # Test print_lead_summary (should execute without exception)
    print_lead_summary(leads[0])
