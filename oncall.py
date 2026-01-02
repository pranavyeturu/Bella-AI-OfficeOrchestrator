# oncall.py
import os
from db import SessionLocal
from models import AssignmentPointer, TicketAssignment
from slack_utils.client import slack_client

# your team’s Slack IDs in rotation order:
ONCALL_ROSTER = [
    "U0917C2HT7A",  
    "U0DEF67890",  
    "U0GHI23456",
      
]

def get_next_oncall():
    db = SessionLocal()
    ptr = db.query(AssignmentPointer).first()
    if not ptr:
        ptr = AssignmentPointer(last_index=-1)
        db.add(ptr)
    idx = (ptr.last_index + 1) % len(ONCALL_ROSTER)
    ptr.last_index = idx
    db.commit()
    db.close()
    return ONCALL_ROSTER[idx]

def find_available_engineer():
    # gather busy engineers
    db = SessionLocal()
    busy = {
        row[0] for row in
        db.query(TicketAssignment.engineer_id)
          .filter(TicketAssignment.resolved_at==None)
          .distinct()
          .all()
    }
    db.close()

    # rotate until we find someone not in busy
    for _ in ONCALL_ROSTER:
        candidate = get_next_oncall()
        if candidate not in busy:
            return candidate
    # if all busy, just return next anyway
    return get_next_oncall()
