# commands_api.py

import os, json, asyncio, re
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
load_dotenv() 
# LLM client
_llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#— Import your existing logic —#
from parser.gpt_parser            import extract_meeting_details
from parser.google_calendar       import (
    load_dummy_credentials,
    get_user_busy_times,
    get_available_slots,
    create_calendar_event,
)
from slack_handlers.tasks         import handle_logtask_command, handle_sendreport_command
from slack_handlers.digest        import handle_summarise_command
from slack_handlers.tickets       import handle_ticket_webhook, handle_resolve_command

from email_map import name_to_email

# ── Intent classification ─────────────────────────────────────────────────────
def classify_intent(nl_text: str) -> str:
    """Ask the LLM which of our six commands this is."""
    prompt = (
        "You are a command router.  Given a user instruction, "
        "choose exactly one of:\n"
        "  schedule_meeting, log_task, send_report, summarise_chat, assign_ticket, resolve_ticket\n"
        f"Instruction:\n\"\"\"\n{nl_text}\n\"\"\"\n"
        "Return only the label."
    )
    resp = _llm.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.0,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

# ── 1) Schedule Meeting ────────────────────────────────────────────────────────
def get_free_slots_nlp(nl_text: str):
    details = extract_meeting_details(nl_text)
    creds   = load_dummy_credentials()
    busy    = get_user_busy_times(creds)

    # parse the timeframe into datetimes
    tf_start = datetime.fromisoformat(details["timeframe"]["start"])
    tf_end   = datetime.fromisoformat(details["timeframe"]["end"])

    slots = get_available_slots(
        busy,
        start_day=tf_start,
        end_day=tf_end,
        slot_minutes=details["duration_minutes"],
    )
    return details, slots[:5]

def choose_slot_nlp(followup: str, slots: list[dict]) -> str:
    lines = "\n".join(f"{i+1}. {s['start']}→{s['end']}" for i,s in enumerate(slots))
    prompt = (
      "You are a scheduler.  Here are available slots:\n\n"
      f"{lines}\n\nUser says: \"{followup}\"\n\n"
      "Return *only* the ISO start timestamp of the slot they picked."
    )
    resp = _llm.chat.completions.create(
      model="gpt-3.5-turbo", temperature=0.0,
      messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

def schedule_meeting_nlp(prompt: str, start_iso: str) -> dict:
    """
    Book a 30-minute meeting at `start_iso` on the user's primary calendar,
    using the same credentials file your slash-command route uses.
    """
    # 1) (Optional) re-extract participants/duration if you want to use them in summary
    details = extract_meeting_details(prompt)

    # 2) Load the OAuth creds you saved from /google/oauth/callback
    creds = load_dummy_credentials()

    # 3) Fire off the Calendar API insert
    event = create_calendar_event(
        start_time_iso = start_iso,
        credentials    = creds,
        summary        = f"Meeting via NLP with {', '.join(details['participants'])}"
    )

    return event

# ── 2) Log Task ────────────────────────────────────────────────────────────────
def run_logtask_nlp(nl_text: str, user_id: str) -> dict:
    # Your handle_logtask_command already does NL parsing internally
    return asyncio.run(handle_logtask_command(nl_text, user_id))

# ── 3) Send Report ────────────────────────────────────────────────────────────
def run_sendreport_nlp() -> dict:
    return asyncio.run(handle_sendreport_command())

# ── 4) Summarise Chat ─────────────────────────────────────────────────────────
def run_summarise_nlp(nl_text: str, user_id: str) -> dict:
    # we assume user mentions the channel ID like "C0123456789" in the text
    m = re.search(r"\b(C[0-9A-Z]+)\b", nl_text)
    if not m:
        raise ValueError("❌ Could not find channel ID in your instruction.")
    channel_id = m.group(1)
    return asyncio.run(handle_summarise_command(channel_id, user_id))

# ── 5) Assign Ticket ──────────────────────────────────────────────────────────
def run_assign_ticket_nlp(nl_text: str) -> dict:
    details = json.loads(
      _llm.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.0,
        messages=[{
          "role":"system",
          "content":(
            "Extract JSON with keys ticket_id, subject, link from:\n"
            f"\"{nl_text}\""
          )
        }]
      ).choices[0].message.content
    )
    return asyncio.run(handle_ticket_webhook(details))

# ── 6) Resolve Ticket ─────────────────────────────────────────────────────────
def run_resolve_ticket_nlp(nl_text: str, user_id: str) -> dict:
    # e.g. "resolved HD-512"
    m = re.search(r"\b([A-Za-z0-9-]+)\b", nl_text)
    if not m:
        raise ValueError("❌ Could not parse ticket ID.")
    ticket_id = m.group(1)
    return asyncio.run(handle_resolve_command(ticket_id, user_id, response_url=None))
