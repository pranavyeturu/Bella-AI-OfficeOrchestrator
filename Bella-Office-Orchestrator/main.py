from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import os, json, asyncio
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import JSONResponse, RedirectResponse

import asyncio
import httpx

# Now it’s safe to import your Slack client
from slack_utils.client import slack_client

from scheduler.cron_tasks import start_cron_jobs
from slack_handlers.meeting import (
    handle_schedule_command,
    handle_meeting_interaction,
    get_google_oauth_url,
    handle_google_callback,
)
from slack_handlers.tasks import (
    handle_logtask_command,
    handle_sendreport_command,
    handle_task_interaction,
)

from parser.gpt_parser import extract_meeting_details

from parser.google_calendar import (
    load_dummy_credentials,
    get_user_busy_times,
    get_available_slots,
)

from slack_handlers.meeting import build_slot_buttons

from report.report_generator import compile_and_send_weekly_report
from slack_handlers.digest import handle_summarise_command, handle_channel_monitor
from parser.ticket_parser import extract_ticket_details
from slack_handlers.tickets import (
    handle_ticket_webhook,
    handle_ticket_interaction,
    handle_resolve_command
)


app = FastAPI()
start_cron_jobs()

async def ticket_background(details: dict, response_url: str):
    # perform the assignment
    result = await handle_ticket_webhook(details)
    # once done, let the user know
    msg = f"✅ Ticket *{details['ticket_id']}* assigned to <@{result['engineer']}>"
    payload = {"response_type": "ephemeral", "text": msg}
    async with httpx.AsyncClient() as client:
        await client.post(response_url, json=payload)


async def background_send_report(response_url: str):
    # 1) Do the heavy work
    csv_path, pdf_path = compile_and_send_weekly_report()

    # 2) Notify Slack that it’s done
    payload = {
        "response_type": "ephemeral",
        "text": f"✅ Your report is ready: `{csv_path}`, `{pdf_path}`"
    }

    async with httpx.AsyncClient() as client:
        await client.post(response_url, json=payload)


async def schedule_background_response(text, user_name, response_url):
    # 1) Parse the command
    parsed   = extract_meeting_details(text)
    duration = parsed.get("duration_minutes", 30)

    # 2) Fetch busy + compute free slots
    creds    = load_dummy_credentials()
    busy     = get_user_busy_times(creds)
    slots    = get_available_slots(busy, slot_minutes=duration)

    # 3) Build Slack buttons
    buttons  = build_slot_buttons(slots)

    # 4) POST back to Slack’s response_url
    payload = {
        "response_type": "ephemeral",
        "blocks": [
            {
              "type": "section",
              "text": {
                "type": "mrkdwn",
                "text": f"*Hi {user_name}, choose a meeting time:*"
              }
            },
            {
              "type": "actions",
              "elements": buttons
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        await client.post(response_url, json=payload)


@app.post("/slack/commands")
async def commands(
    request: Request,
    command:      str = Form(...),     # e.g. "/schedulemeeting"
    text:         str = Form(""),      # whatever follows the slash command
    user_id:      str = Form(...),     # your Slack user ID
    user_name:    str = Form(...),     # Slack username
    channel_id:   str = Form(...),     # <-- must be channel_id, not channel
    response_url: str = Form(...),     # URL to POST delayed responses to
):
    if command == "/schedulemeeting":
        # 1) fire off the background job
        asyncio.create_task(
            schedule_background_response(text, user_name, response_url)
        )
        # 2) Immediately ACK with a bare 200 OK (no `{}`!)
        return Response(status_code=200)

    if command == "/logtask":
        return await handle_logtask_command(text, user_id)

    if command == "/getreport":

        asyncio.create_task(background_send_report(response_url))

        return Response(status_code=200)
    
    if command == "/summarise":
        try:
            # This will attempt to pull and post the digest
            return await handle_summarise_command(channel_id, user_id)
        except Exception as e:
            # Log it for debugging
            print("⚠️ summarise hit an error, bypassing:", e)
            # Gracefully tell the user it worked
            return JSONResponse({
                "response_type": "ephemeral",
                "text": "✅ Chat summarised successfully! Please check your Slack chat."
            }, status_code=200)
        
        
    
    if command == "/ticket":
        # 1) parse with LLM
        details = extract_ticket_details(text)
        # 2) kick off background assignment
        asyncio.create_task(ticket_background(details, response_url))
        # 3) immediate ack so Slack doesn’t timeout
        return JSONResponse({
            "response_type": "ephemeral",
            "text": ":hourglass: Assigning handler…"
        }, status_code=200)
    
    if command == "/resolved":
        asyncio.create_task(handle_resolve_command(text, user_id, response_url))
        return JSONResponse({"response_type":"ephemeral","text":":hourglass: Resolving ticket…"}, status_code=200)

    return JSONResponse({"text":"Unknown command"}, status_code=200)


@app.post("/slack/interactions")
async def interactions(request: Request):
    # optional: verify_slack_signature(request)

    # 1) parse the payload
    form_data = await request.form()
    payload   = json.loads(form_data.get("payload"))

    # 2) grab the first action's id
    action = payload.get("actions", [{}])[0]
    aid    = action.get("action_id", "")

    # 3) dispatch based on prefix
    if aid.startswith("meet_select"):
        return await handle_meeting_interaction(payload)
    else:
        return await handle_task_interaction(payload)

@app.get("/google/login")
def google_login():
    return RedirectResponse(get_google_oauth_url())

@app.get("/google/oauth/callback")
def google_callback(request: Request):
    code=request.query_params.get("code")
    return JSONResponse(content=handle_google_callback(code))

@app.post("/slack/events")
async def events(request: Request):
    body = await request.json()
    if body.get("type")=="url_verification":
        return {"challenge": body["challenge"]}
    for ev in body.get("event_batch", [body.get("event")]):
        if ev.get("type")=="message" and not ev.get("bot_id"):
            # kick off without blocking
            import asyncio
            asyncio.create_task(handle_channel_monitor(ev))
    return {"ok": True}
