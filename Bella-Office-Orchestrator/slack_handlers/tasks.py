# slack_handlers/tasks.py
import json
import asyncio
from fastapi.responses import JSONResponse
from jira.jira_api import fetch_user_tasks, get_incomplete_tasks, add_worklog, mark_done
from report.report_generator import compile_and_send_weekly_report
from ai_utils import summarize_overdue_tasks

from sqlalchemy.orm import Session
from parser.log_parser import extract_log_details
from db import SessionLocal
from models import LogEntry

# map Slack ID → Jira email & name
SLACK_TO_JIRA = {
    "U12345": ("alice@domain.com","Alice"),
    "U67890": ("bob@domain.com","Bob")
}


async def handle_logtask_command(text: str, user_id: str):
    """
    Called by `/logtask` slash-command.  Parses + inserts into DB.
    """
    try:
        details = extract_log_details(text)
        issue   = details["issue"]
        mins    = int(details["minutes"])
    except Exception as e:
        return JSONResponse({"text": f":warning: {e}"}, status_code=200)

    # save to DB
    db: Session = SessionLocal()
    entry = LogEntry(user_id=user_id, issue=issue, minutes=mins)
    db.add(entry)
    db.commit()
    db.close()

    return JSONResponse({
        "response_type": "ephemeral",
        "text": f"✅ Logged *{mins}m* to *{issue}*."
    }, status_code=200)

async def handle_sendreport_command():
    csv_path,pdf_path = compile_and_send_weekly_report()
    return JSONResponse({"response_type":"ephemeral",
                         "text":f"✅ Report sent! `{csv_path}`, `{pdf_path}`"})

async def handle_task_interaction(payload):
    action = payload["actions"][0]
    aid, key = action["action_id"], action["value"]
    if aid=="mark_done":
        resp=mark_done(key)
        text=(":white_check_mark: Marked done" if resp.ok else ":x: Failed")
    else:  # log_time
        resp=add_worklog(key,60,comment="Auto-logged 60m")
        text=(":hourglass: Logged 60m" if resp.ok else ":x: Failed")
    return JSONResponse({"response_type":"ephemeral","text":text})

async def send_laggard_reminders():
    for sid,(email,name) in SLACK_TO_JIRA.items():
        tasks = fetch_user_tasks(email)
        laggards = get_incomplete_tasks(tasks)
        if not laggards: continue
        text   = await summarize_overdue_tasks(laggards,name)
        blocks =[{"type":"section","text":{"type":"mrkdwn","text":text}}]
        for i in laggards:
            blocks.append({"type":"actions","elements":[
                {"type":"button","action_id":"mark_done","text":{"type":"plain_text","text":"✅ Done"},"value":i["key"]},
                {"type":"button","action_id":"log_time","text":{"type":"plain_text","text":"🕒 60m"},"value":i["key"]}
            ]})
        from slack_utils.client import slack_client
        slack_client.chat_postMessage(channel=sid,blocks=blocks)
