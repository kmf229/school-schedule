# Compatible with Python 3.8
# pip install ics python-dateutil pyyaml requests python-dotenv

import argparse
import re
import sys
import os
import requests
import yaml
from datetime import date, datetime, timedelta, timezone, time as dtime
from dateutil.tz import gettz
from ics import Calendar
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ====== CONFIG ======
ICS_URL = "https://doyle.cbsd.org/fs/calendar-manager/events.ics?calendar_ids=6"
LOCAL_TZ = gettz("America/New_York")

ANCHOR_DATE = date(2025, 9, 2)   # first instructional day
ANCHOR_CYCLE = 1                 # cycle day for that date

LIBRARY_DAYS = {
    "Aiden (Day 2 library)": {2},
    "Averie (Day 3 library)": {3},
}

MANUAL_FILE = "manual_off_days.yaml"

# Textbelt config (use environment variables for security)
TEXTBELT_API_KEY = os.getenv("TEXTBELT_API_KEY")  # Optional for paid plans
TO_PHONE_NUMBER = os.getenv("TO_PHONE_NUMBER")

NO_SCHOOL_PATTERNS = [
    r"\bno school\b",
    r"\bschool closed\b",
    r"\bholiday\b",
    r"\bsnow day\b",
    r"\binclement weather\b",
    r"\b(in[-\s]?service|teacher work day)\b",
]
NO_SCHOOL_RE = re.compile("|".join(NO_SCHOOL_PATTERNS), re.I)


# ====== UTIL ======
def is_weekend(d):
    return d.weekday() >= 5

def load_manual_off_days():
    if not os.path.exists(MANUAL_FILE):
        return set()
    with open(MANUAL_FILE, "r") as f:
        data = yaml.safe_load(f) or {}
    return {date.fromisoformat(s) for s in data.get("extra_no_school", [])}

def save_manual_off_days(days):
    with open(MANUAL_FILE, "w") as f:
        yaml.safe_dump({"extra_no_school": sorted(d.isoformat() for d in days)}, f)

def fetch_calendar(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Calendar(r.text)

def fetch_ics_no_school_dates(url):
    cal = fetch_calendar(url)
    out = set()
    for ev in cal.events:
        summary = (ev.name or "").strip()
        start_dt = ev.begin.datetime if hasattr(ev.begin, "datetime") else datetime.combine(ev.begin.date(), datetime.min.time(), tzinfo=timezone.utc)
        end_dt   = ev.end.datetime   if hasattr(ev.end, "datetime")   else datetime.combine(ev.end.date(),   datetime.min.time(), tzinfo=timezone.utc)
        start_d = start_dt.astimezone(LOCAL_TZ).date()
        end_excl = end_dt.astimezone(LOCAL_TZ).date()
        if NO_SCHOOL_RE.search(summary):
            d = start_d
            while d < end_excl:
                out.add(d)
                d += timedelta(days=1)
    return out

def cycle_day_on(target, anchor_date, anchor_cycle, no_school):
    if target == anchor_date:
        return anchor_cycle
    cycle = anchor_cycle
    step = 1 if target > anchor_date else -1
    d = anchor_date
    while d != target:
        d = d + timedelta(days=step)
        if not is_weekend(d) and d not in no_school:
            if step == 1:
                cycle = 1 if cycle == 5 else cycle + 1
            else:
                cycle = 5 if cycle == 1 else cycle - 1
    return cycle

def instructional_day(d, no_school):
    return (not is_weekend(d)) and (d not in no_school)

def who_needs_library(cycle):
    return [name for name, days in LIBRARY_DAYS.items() if cycle in days]

def send_sms(message):
    """Send SMS via Textbelt. Falls back to print if phone number not configured."""
    if not TO_PHONE_NUMBER:
        print("Phone number not configured. Printing instead:")
        print(message)
        return
    
    # Textbelt API endpoint
    url = "https://textbelt.com/text"
    
    # Prepare the payload
    payload = {
        "phone": TO_PHONE_NUMBER.strip(),
        "message": message,
    }
    
    # Add API key - use provided key or free "textbelt" key
    if TEXTBELT_API_KEY:
        payload["key"] = TEXTBELT_API_KEY
        print("Using Textbelt with provided API key")
    else:
        payload["key"] = "textbelt"
        print("Using Textbelt free quota (1 text per day per IP)")
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        result = response.json()
        
        if result.get("success"):
            print(f"SMS sent successfully via Textbelt. ID: {result.get('textId', 'unknown')}")
            if result.get("quotaRemaining") is not None:
                print(f"Quota remaining: {result['quotaRemaining']}")
        else:
            print(f"Failed to send SMS: {result.get('error', 'Unknown error')}")
            print("Message content:")
            print(message)
            
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        print("Message content:")
        print(message)

# ---- Event helpers ----
def _local_dt(dt_like):
    if hasattr(dt_like, "datetime"):
        return dt_like.datetime.astimezone(LOCAL_TZ)
    return datetime.combine(dt_like.date(), dtime.min, tzinfo=LOCAL_TZ)

def _is_all_day_ev(ev):
    try:
        if hasattr(ev, "all_day") and ev.all_day:
            return True
    except Exception:
        pass
    begin_dt = _local_dt(ev.begin)
    end_dt_excl = _local_dt(ev.end)
    span = end_dt_excl - begin_dt
    return begin_dt.time() == dtime.min and span.days >= 1 and end_dt_excl.time() == dtime.min

def events_on_date(target_date, cal):
    """Return events that fall on `target_date` (local)."""
    results = []
    day_start = datetime.combine(target_date, dtime.min, tzinfo=LOCAL_TZ)
    day_end_excl = day_start + timedelta(days=1)

    for ev in cal.events:
        name = (getattr(ev, "name", "") or "").strip()
        loc = getattr(ev, "location", None)
        desc = getattr(ev, "description", None)

        if _is_all_day_ev(ev):
            # For all-day events, use the raw date without timezone conversion
            start_d = ev.begin.date()
            end_d_excl = ev.end.date()
            if start_d <= target_date < end_d_excl:
                results.append({
                    "title": name,
                    "all_day": True,
                    "start": day_start,
                    "end_exclusive": day_end_excl,
                    "location": loc,
                    "description": desc,
                })
        else:
            ev_start = _local_dt(ev.begin)
            ev_end_excl = _local_dt(ev.end)
            if (ev_start < day_end_excl) and (ev_end_excl > day_start):
                show_start = max(ev_start, day_start)
                show_end_excl = min(ev_end_excl, day_end_excl)
                results.append({
                    "title": name,
                    "all_day": False,
                    "start": show_start,
                    "end_exclusive": show_end_excl,
                    "location": loc,
                    "description": desc,
                })

    results.sort(key=lambda e: (not e["all_day"], e["start"]))
    return results

def format_event_line(ev):
    if ev["all_day"]:
        when = "All day"
    else:
        s = ev["start"].strftime("%-I:%M %p")
        e = (ev["end_exclusive"] - timedelta(seconds=1)).strftime("%-I:%M %p")
        when = f"{s}–{e}"
    loc = f" @ {ev['location']}" if ev.get("location") else ""
    return f"- {when}: {ev['title']}{loc}"


# ====== DAILY SUMMARY ======
def get_daily_summary_message(target):
    """Generate daily summary as a string for SMS or printing."""
    cal = fetch_calendar(ICS_URL)
    ics_block = fetch_ics_no_school_dates(ICS_URL)
    manual = load_manual_off_days()
    no_school = ics_block | manual

    cyc = cycle_day_on(target, ANCHOR_DATE, ANCHOR_CYCLE, no_school)
    message = f"{target:%A %b %d, %Y}: Cycle Day {cyc}\n"

    if instructional_day(target, no_school):
        names = who_needs_library(cyc)
        if names:
            message += "Library reminder for:\n"
            for n in names:
                message += f" • {n}\n"
        else:
            message += "No library reminders.\n"

        todays_events = events_on_date(target, cal)
        if todays_events:
            message += "\nSchool events:\n"
            for ev in todays_events:
                message += format_event_line(ev) + "\n"
        else:
            message += "\nSchool events: none listed.\n"
    else:
        message += "Not an instructional day.\n"
        todays_events = events_on_date(target, cal)
        if todays_events:
            message += "\nSchool events (non-instructional):\n"
            for ev in todays_events:
                message += format_event_line(ev) + "\n"
    
    return message.strip()

def print_daily_summary(target):
    """Print daily summary to console."""
    message = get_daily_summary_message(target)
    print(message)

def send_daily_summary(target):
    """Send daily summary via SMS."""
    message = get_daily_summary_message(target)
    send_sms(message)

def print_events_only(target):
    cal = fetch_calendar(ICS_URL)
    evs = events_on_date(target, cal)
    print(f"Events on {target:%A %b %d, %Y}:")
    if not evs:
        print(" (none)")
        return
    for ev in evs:
        print(format_event_line(ev))


# ====== CLI ACTIONS ======
def cmd_today():
    today = datetime.now(LOCAL_TZ).date()
    print_daily_summary(today)

def cmd_tomorrow():
    today = datetime.now(LOCAL_TZ).date()
    print_daily_summary(today + timedelta(days=1))

def cmd_sms_today():
    today = datetime.now(LOCAL_TZ).date()
    send_daily_summary(today)

def cmd_sms_tomorrow():
    today = datetime.now(LOCAL_TZ).date()
    send_daily_summary(today + timedelta(days=1))

def cmd_check(target_str):
    print_daily_summary(date.fromisoformat(target_str))

def cmd_add_off(d):
    days = load_manual_off_days()
    days.add(d)
    save_manual_off_days(days)
    print(f"Added manual off-day: {d.isoformat()}")

def cmd_list_off():
    days = sorted(load_manual_off_days())
    if not days:
        print("No manual off-days saved.")
    else:
        print("Manual off-days:")
        for d in days:
            print(" •", d.isoformat())


# ====== MAIN ======
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="5-Day rotation with manual off-days + event listing.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--today", action="store_true", help="Show today's cycle, library reminder, and events")
    g.add_argument("--tomorrow", action="store_true", help="Show tomorrow's cycle, library reminder, and events")
    g.add_argument("--sms-today", action="store_true", help="Send today's info via SMS")
    g.add_argument("--sms-tomorrow", action="store_true", help="Send tomorrow's info via SMS")
    g.add_argument("--check", type=str, help="Check a specific date YYYY-MM-DD (cycle, library, events)")
    g.add_argument("--events", type=str, help="List only events for a specific date YYYY-MM-DD")
    g.add_argument("--add-off", type=str, help="Add manual off-day YYYY-MM-DD")
    g.add_argument("--list-off", action="store_true", help="List manual off-days")

    args = p.parse_args()

    if args.today:
        cmd_today()
    elif args.tomorrow:
        cmd_tomorrow()
    elif args.sms_today:
        cmd_sms_today()
    elif args.sms_tomorrow:
        cmd_sms_tomorrow()
    elif args.check:
        cmd_check(args.check)
    elif args.events:
        print_events_only(date.fromisoformat(args.events))
    elif args.add_off:
        cmd_add_off(date.fromisoformat(args.add_off))
    elif args.list_off:
        cmd_list_off()
    else:
        p.print_help()
        sys.exit(0)
