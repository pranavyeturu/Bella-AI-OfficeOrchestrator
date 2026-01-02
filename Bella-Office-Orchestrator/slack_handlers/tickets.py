# slack_handlers/tickets.py

import json
from datetime import datetime
from fastapi.responses import JSONResponse
from db import SessionLocal
from models import TicketAssignment
from oncall import find_available_engineer
from ticket_api import assign_ticket, add_internal_note, resolve_ticket
from slack_utils.client import slack_client
from slack_sdk.errors import SlackApiError

import httpx
from typing import Optional
from sqlalchemy.exc import IntegrityError

async def handle_ticket_webhook(payload: dict):
    # only urgent

    tid      = payload["ticket_id"]
    subject  = payload.get("subject","(no subject)")
    link     = payload.get("link")
    engineer = find_available_engineer()

    # 1) assign & note in ticket system
    assign_ticket(tid, engineer)
    add_internal_note(tid, f"Auto-assigned to <@{engineer}>")

    # ── OPEN A DM CONVERSATION ───────────────────────────────────────────────
    try:
        # ask Slack to open (or return) the IM channel for that user
        im = slack_client.conversations_open(users=[engineer])
        dm_channel = im["channel"]["id"]
    except SlackApiError as e:
        # if even this fails, fall back to the channel they came from, or just bail
        print("❌ Could not open DM for", engineer, e)
        return {"status":"error", "reason":"cannot_open_dm"}

    # ── SEND THE DM ──────────────────────────────────────────────────────────
    blocks = [
      {"type":"section", "text":{"type":"mrkdwn",
        "text": f":rotating_light: *Urgent ticket* <{link}|{tid}> — {subject}"
      }},
      {"type":"actions", "elements":[
         {"type":"button","action_id":"accept_ticket",
           "text":{"type":"plain_text","text":"Accept"},
           "style":"primary","value":tid},
         {"type":"button","action_id":"escalate_ticket",
           "text":{"type":"plain_text","text":"Escalate"},
           "style":"danger","value":tid}
      ]}
    ]
    try:
        slack_client.chat_postMessage(
            channel=dm_channel,
            text=f"Urgent ticket {tid}: {subject}",
            blocks=blocks
        )
    except SlackApiError as e:
        print("❌ Failed to post DM:", e)
        # swallow or handle as you prefer

    return {"status":"assigned","engineer":engineer}

    # 2) record in DB
    db = SessionLocal()
    try:
        existing = db.query(TicketAssignment)\
                     .filter_by(ticket_id=tid)\
                     .first()
        if existing:
            # update the engineer & reset resolved_at
            existing.engineer_id = engineer
            existing.assigned_at = datetime.utcnow()
            existing.resolved_at = None
        else:
            new = TicketAssignment(
                ticket_id   = tid,
                engineer_id = engineer
            )
            db.add(new)
        db.commit()

    except IntegrityError:
        db.rollback()
        # (shouldn't happen now, but just in case)
    finally:
        db.close()

    # 3) DM them with Accept/Escalate buttons
    blocks = [
      {"type":"section",
       "text":{"type":"mrkdwn",
         "text": f":rotating_light: *Urgent ticket* <{link}|{tid}> — {subject}"
       }},
      {"type":"actions","elements":[
         {"type":"button",
          "action_id":"accept_ticket",
          "text":{"type":"plain_text","text":"Accept"},
          "style":"primary","value":tid},
         {"type":"button",
          "action_id":"escalate_ticket",
          "text":{"type":"plain_text","text":"Escalate"},
          "style":"danger","value":tid}
      ]}
    ]
    slack_client.chat_postMessage(
        channel=engineer,
        text=f"New urgent ticket {tid}",
        blocks=blocks
    )

    return {"status":"assigned","engineer":engineer}


async def handle_ticket_interaction(payload: dict):
    action = payload["actions"][0]
    tid    = action["value"]
    user   = payload["user"]["id"]

    if action["action_id"] == "accept_ticket":
        resolve = False
        add_internal_note(tid, f"{user} has *accepted* the ticket.")
        assign_ticket(tid, user)  # reassign if needed
        text = f":white_check_mark: <@{user}> accepted ticket *{tid}*."
    else:  # escalate_ticket
        add_internal_note(tid, f"{user} escalated the ticket.")
        new_eng = find_available_engineer()
        assign_ticket(tid, new_eng)
        text = f":rotating_light: <@{user}> escalated. New assignee: <@{new_eng}>."

    # update the original Slack message
    slack_client.chat_update(
      channel=payload["container"]["channel_id"],
      ts     =payload["container"]["message_ts"],
      text   =text,
      blocks =[{"type":"section","text":{"type":"mrkdwn","text":text}}]
    )
    return JSONResponse(status_code=200, content={})


# New: resolve handler for `/resolved`
async def handle_resolve_command(
    ticket_id: str,
    user_id: str,
    response_url: Optional[str] = None
) -> dict:
    """
    Marks a ticket resolved:
     - in your ticket system
     - in the DB
     - if response_url given, posts back to Slack
    Returns the payload dict so callers (like Streamlit) can inspect it.
    """
    # 1) resolve in ticket system
    resolve_ticket(ticket_id)
    add_internal_note(ticket_id, f"Ticket resolved by <@{user_id}>")

    # 2) mark in DB
    db = SessionLocal()
    rec = (
        db.query(TicketAssignment)
          .filter_by(ticket_id=ticket_id, engineer_id=user_id, resolved_at=None)
          .first()
    )
    if rec:
        rec.resolved_at = datetime.utcnow()
        db.commit()
    db.close()

    # 3) prepare Slack payload
    payload = {
        "response_type": "ephemeral",
        "text": f"✅ <@{user_id}> marked *{ticket_id}* as resolved."
    }

    # 4) only post back if Slack gave us a URL
    if response_url:
        async with httpx.AsyncClient() as client:
            await client.post(response_url, json=payload)

    # return so Streamlit can show it too
    return payload
