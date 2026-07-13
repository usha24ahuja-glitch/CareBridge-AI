import os
import json
import logging
import datetime
import time
import threading
from typing import Dict, List, Any
from slack_sdk import WebClient

logger = logging.getLogger(__name__)

DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "completed_screenings.json"))

def save_screening(evaluation: Dict[str, Any]) -> None:
    """Appends a completed screening evaluation record to the persistent store."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        records = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    records = json.load(f)
            except Exception as e:
                logger.error("Error reading completed screenings database: %s", e)
                records = []
                
        records.append(evaluation)
        
        with open(DATA_FILE, "w") as f:
            json.dump(records, f, indent=2)
            
        logger.info("Successfully saved screening record for beneficiary: %s", evaluation.get("beneficiary_id"))
    except Exception as e:
        logger.error("Failed to save screening record: %s", e, exc_info=True)

def generate_summary_digest() -> str:
    """Computes and formats the dashboard screening summary metrics."""
    try:
        records = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    records = json.load(f)
            except Exception as e:
                logger.error("Error loading screenings for dashboard generation: %s", e)
                
        now = datetime.datetime.now()
        today_str = now.strftime("%B %d, %Y")
        
        # Calculate time windows in timezone-aware local time
        # Start of today (local time)
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        # Start of the current week (Monday, local time)
        start_of_week = (start_of_today - datetime.timedelta(days=now.weekday())).astimezone()
        
        screenings_today = 0
        cancelled_today = 0
        screenings_week = 0
        cancelled_week = 0
        flag_breakdown: Dict[str, int] = {
            "Housing": 0,
            "Food": 0,
            "Transportation": 0,
            "Utilities": 0,
            "Safety": 0
        }
        
        for r in records:
            ts_str = r.get("timestamp")
            if not ts_str:
                continue
                
            try:
                # Handle trailing Z for older Python fromisoformat compatibility
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                dt = datetime.datetime.fromisoformat(ts_str)
                # Convert to local timezone of the running server to compare
                local_dt = dt.astimezone()
            except Exception as e:
                logger.error("Failed to parse timestamp %s: %s", ts_str, e)
                continue
                
            status = r.get("status", "Completed")
            
            if local_dt >= start_of_today:
                if status == "Cancelled":
                    cancelled_today += 1
                else:
                    screenings_today += 1
            if local_dt >= start_of_week:
                if status == "Cancelled":
                    cancelled_week += 1
                else:
                    screenings_week += 1
                    for flag in r.get("flags", []):
                        if flag in flag_breakdown:
                            flag_breakdown[flag] += 1
                            
        # Calculate completion rate this week
        total_started_week = screenings_week + cancelled_week
        if total_started_week > 0:
            completion_rate = (screenings_week / total_started_week) * 100
            completion_rate_str = f"{completion_rate:.1f}%"
        else:
            completion_rate_str = "N/A"
                        
        # Format domain flagged breakdown string
        flagged_parts = []
        for domain in ["Housing", "Food", "Transportation", "Utilities", "Safety"]:
            count = flag_breakdown[domain]
            if count > 0:
                flagged_parts.append(f"{domain} ({count})")
                
        if flagged_parts:
            needs_str = ", ".join(flagged_parts)
        else:
            needs_str = "None"
            
        digest = (
            f"📊 Daily HRSN Screening Summary — {today_str}\n"
            f"• Screenings completed today: {screenings_today}\n"
            f"• Screenings cancelled today: {cancelled_today}\n"
            f"• Total completed this week: {screenings_week}\n"
            f"• Completion rate this week: {completion_rate_str}\n"
            f"• Needs flagged this week: {needs_str}"
        )
        return digest
    except Exception as e:
        logger.error("Error generating summary digest: %s", e, exc_info=True)
        return "⚠️ *Error*: Failed to generate the screening summary digest."

def run_scheduler(client: WebClient, target_hour: int = 17, target_minute: int = 0, interval_seconds: int = 0) -> None:
    """Starts a background daemon thread that posts the digest to #leadership-dashboard.
    
    If interval_seconds > 0, it posts every interval_seconds (useful for rapid testing).
    Otherwise, it checks once a day at the target hour:minute local time.
    """
    def scheduler_loop():
        logger.info(
            "Dashboard scheduler loop running (Target: %02d:%02d, Test Interval: %d sec)",
            target_hour, target_minute, interval_seconds
        )
        last_posted_date = None
        
        while True:
            try:
                if interval_seconds > 0:
                    time.sleep(interval_seconds)
                    logger.info("Scheduled test execution triggered.")
                    digest = generate_summary_digest()
                    client.chat_postMessage(channel="#leadership-dashboard", text=digest)
                else:
                    now = datetime.datetime.now()
                    # Check if it's 5:00 PM local time and we haven't posted today yet
                    if now.hour == target_hour and now.minute == target_minute:
                        current_date = now.date()
                        if last_posted_date != current_date:
                            logger.info("Daily scheduled dashboard post triggered.")
                            digest = generate_summary_digest()
                            client.chat_postMessage(channel="#leadership-dashboard", text=digest)
                            last_posted_date = current_date
                    time.sleep(30)
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)
                time.sleep(10)
                
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
