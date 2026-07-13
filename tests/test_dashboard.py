import os
import json
import datetime
import pytest
from unittest.mock import MagicMock
import src.dashboard
from src.dashboard import save_screening, generate_summary_digest, run_scheduler

@pytest.fixture
def temp_data_file(tmp_path):
    """Fixture to isolate the dashboard JSON database file during tests."""
    original_data_file = src.dashboard.DATA_FILE
    temp_file = os.path.abspath(os.path.join(tmp_path, "completed_screenings.json"))
    src.dashboard.DATA_FILE = temp_file
    yield temp_file
    src.dashboard.DATA_FILE = original_data_file

def test_save_screening(temp_data_file):
    """Tests that evaluations are written to the database file correctly."""
    evaluation = {
        "beneficiary_id": "C1234",
        "flags": ["Housing", "Food"],
        "timestamp": "2026-07-12T01:34:23+00:00",
        "screened_by": "U111",
        "status": "Completed"
    }
    
    # Save once
    save_screening(evaluation)
    assert os.path.exists(temp_data_file)
    
    with open(temp_data_file, "r") as f:
        records = json.load(f)
    assert len(records) == 1
    assert records[0]["beneficiary_id"] == "C1234"
    assert records[0]["flags"] == ["Housing", "Food"]
    assert records[0]["status"] == "Completed"

def test_generate_summary_digest(temp_data_file):
    """Tests date window calculation, completed/cancelled counts, and breakdown formatting."""
    # Calculate timezone-aware local now to match dashboard logic
    now_aware = datetime.datetime.now().astimezone()
    
    # 1. Completed screening today (1 hour ago)
    ts_today = (now_aware - datetime.timedelta(hours=1)).isoformat()
    record_today = {
        "beneficiary_id": "PAT-TODAY",
        "flags": ["Housing", "Food"],
        "timestamp": ts_today,
        "screened_by": "U1",
        "status": "Completed"
    }
    
    # 2. Cancelled screening today (30 mins ago)
    ts_cancel_today = (now_aware - datetime.timedelta(minutes=30)).isoformat()
    record_cancel_today = {
        "beneficiary_id": "Anonymous",
        "flags": [],
        "timestamp": ts_cancel_today,
        "screened_by": "U1",
        "status": "Cancelled"
    }
    
    # 3. Completed screening earlier this week
    # Ensure this stays within the same Monday-Sunday calendar week
    weekday_offset = now_aware.weekday()
    if weekday_offset > 0:
        days_offset = min(weekday_offset, 3)
        ts_week = (now_aware - datetime.timedelta(days=days_offset, hours=2)).isoformat()
    else:
        # If today is Monday, keep it on the same day but slightly earlier than today's records
        ts_week = (now_aware - datetime.timedelta(minutes=45)).isoformat()
        
    record_week = {
        "beneficiary_id": "PAT-WEEK",
        "flags": ["Food", "Transportation"],
        "timestamp": ts_week,
        "screened_by": "U1",
        "status": "Completed"
    }
    
    # 4. Screening completed last week (10 days ago) - should be ignored
    ts_last_week = (now_aware - datetime.timedelta(days=10)).isoformat()
    record_old = {
        "beneficiary_id": "PAT-OLD",
        "flags": ["Safety"],
        "timestamp": ts_last_week,
        "screened_by": "U1",
        "status": "Completed"
    }
    
    save_screening(record_today)
    save_screening(record_cancel_today)
    save_screening(record_week)
    save_screening(record_old)
    
    digest = generate_summary_digest()
    
    # Assert counts
    expected_completed_today = 2 if weekday_offset == 0 else 1
    assert f"Screenings completed today: {expected_completed_today}" in digest
    assert "Screenings cancelled today: 1" in digest
    assert "Total completed this week: 2" in digest
    # Completed this week: 2 (PAT-TODAY, PAT-WEEK). Cancelled this week: 1 (Anonymous). Total started: 3.
    # Completion rate: 2 / 3 * 100 = 66.7%
    assert "Completion rate this week: 66.7%" in digest
    
    # Assert breakdown mapping (Housing: 1, Food: 2, Transportation: 1)
    assert "Housing (1)" in digest
    assert "Food (2)" in digest
    assert "Transportation (1)" in digest
    # Ensure old flags (Safety) are not in the breakdown for this week
    assert "Safety" not in digest

def test_generate_summary_digest_empty(temp_data_file):
    """Tests empty state handling when no records exist."""
    digest = generate_summary_digest()
    assert "Screenings completed today: 0" in digest
    assert "Screenings cancelled today: 0" in digest
    assert "Total completed this week: 0" in digest
    assert "Completion rate this week: N/A" in digest
    assert "Needs flagged this week: None" in digest

def test_run_scheduler_test_interval():
    """Tests that the background scheduler loop triggers callbacks correctly in test mode."""
    client_mock = MagicMock()
    
    # Start scheduler with a 1-second interval to check if it posts to Slack
    run_scheduler(client=client_mock, interval_seconds=1)
    
    # Wait for the background loop to trigger at least once
    import time
    time.sleep(1.5)
    
    assert client_mock.chat_postMessage.call_count >= 1
    post_kwargs = client_mock.chat_postMessage.call_args.kwargs
    assert post_kwargs["channel"] == "#leadership-dashboard"
    assert "Daily HRSN Screening Summary" in post_kwargs["text"]
