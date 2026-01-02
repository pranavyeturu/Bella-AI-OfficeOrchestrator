from googleapiclient.discovery import build
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import pytz
import pickle


def load_dummy_credentials():
    """
    Load Google OAuth credentials previously saved to user_creds.pkl
    """
    with open("user_creds.pkl", "rb") as f:
        return pickle.load(f)


def get_user_busy_times(credentials):
    service = build("calendar", "v3", credentials=credentials)

    now = datetime.utcnow()
    end = now + timedelta(days=3)

    body = {
        "timeMin": now.isoformat() + "Z",
        "timeMax": end.isoformat() + "Z",
        "items": [{"id": "primary"}]
    }

    events_result = service.freebusy().query(body=body).execute()
    busy_times = events_result['calendars']['primary']['busy']
    
    return busy_times

def get_available_slots(busy_times, start_day=None, end_day=None, slot_minutes: int=30):
    
    tz = pytz.UTC

    # 1) Normalize start_day to UTC-aware (or default to “now UTC”)
    if start_day:
        now = start_day if start_day.tzinfo else start_day.replace(tzinfo=tz)
    else:
        now = datetime.utcnow().replace(tzinfo=tz)

    # 2) Normalize end_day to UTC-aware (or default to 3 days from now)
    if end_day:
        end = end_day if end_day.tzinfo else end_day.replace(tzinfo=tz)
    else:
        end = now + timedelta(days=3)

    WORKDAY_START = 9  # 9AM
    WORKDAY_END = 18   # 6PM

    # Normalize busy times
    busy_intervals = []
    for b in busy_times:
        busy_intervals.append({
            "start": datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
            "end": datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
        })

    # Sort busy intervals
    busy_intervals.sort(key=lambda x: x["start"])

    # Initialize time cursor
    slots = []
    cursor = now

    while cursor < end:
        day_start = cursor.replace(hour=WORKDAY_START, minute=0, second=0, microsecond=0)
        day_end = cursor.replace(hour=WORKDAY_END, minute=0, second=0, microsecond=0)

        # Skip if outside work hours
        if cursor > day_end:
            cursor = (cursor + timedelta(days=1)).replace(hour=WORKDAY_START)
            continue

        slot_end = cursor + timedelta(minutes=slot_minutes)

        # Skip if slot goes past day end
        if slot_end > day_end:
            cursor = (cursor + timedelta(days=1)).replace(hour=WORKDAY_START)
            continue

        # Check if slot overlaps with any busy period
        overlap = False
        for interval in busy_intervals:
            if interval["start"] < slot_end and interval["end"] > cursor:
                overlap = True
                cursor = interval["end"]
                break

        if not overlap:
            slots.append({
                "start": cursor.isoformat(),
                "end": slot_end.isoformat()
            })
            cursor += timedelta(minutes=slot_minutes)

    return slots

def create_calendar_event(start_time_iso, credentials, summary, attendees_emails=[], timezone="UTC"):
    from googleapiclient.discovery import build
    from datetime import timedelta

    service = build("calendar", "v3", credentials=credentials)

    # Set start/end in IST
    start_dt = datetime.fromisoformat(start_time_iso).astimezone(pytz.timezone(timezone))
    end_dt   = start_dt + timedelta(minutes=30)  # or your duration

    event = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": timezone},
        "attendees": [{"email": e} for e in attendees_emails],
        "reminders": {"useDefault": True},
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return created_event
