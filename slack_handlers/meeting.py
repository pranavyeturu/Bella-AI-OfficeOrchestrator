# slack_handlers/meeting.py
import os,json,pickle,asyncio
from datetime import datetime
from google_auth_oauthlib.flow import Flow
from fastapi.responses import JSONResponse, RedirectResponse
from slack_utils.client import slack_client
from parser.gpt_parser import extract_meeting_details
from parser.google_calendar import (
    load_dummy_credentials,
    get_user_busy_times,
    get_available_slots,
    create_calendar_event
)
from email_map import name_to_email
import httpx,pytz

local_tz = pytz.timezone("Asia/Kolkata")
user_participant_map = {}

def get_google_oauth_url():
    flow = Flow.from_client_config({
        "web":{
            "client_id":os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "redirect_uris":[os.getenv("GOOGLE_REDIRECT_URI")]
        }
    }, scopes=[
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly"
    ])
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    url,_ = flow.authorization_url(
        prompt="consent",access_type="offline",include_granted_scopes=True
    )
    return url

def handle_google_callback(code: str):
    flow = Flow.from_client_config({
        "web":{
            "client_id":os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "redirect_uris":[os.getenv("GOOGLE_REDIRECT_URI")]
        }
    }, scopes=[
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly"
    ])
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open("user_creds.pkl","wb") as f:
        pickle.dump(creds,f)
    busy = get_user_busy_times(creds)
    slots = get_available_slots(busy,slot_minutes=30)
    return {"available_slots": slots[:5]}

def build_slot_buttons(slots):
    buttons = []
    for idx, slot in enumerate(slots[:5]):
        # convert UTC to local label...
        start_label = datetime.fromisoformat(slot["start"].replace("Z","+00:00")) \
                           .astimezone(local_tz) \
                           .strftime("%a %I:%M %p")

        buttons.append({
            "type": "button",
            "action_id": f"meet_select_{idx}",   # <<< ADD THIS
            "text": {"type": "plain_text", "text": start_label},
            "value": slot["start"]
        })
    return buttons

async def handle_schedule_command(text, user_id, user_name, response_url):
    parsed = extract_meeting_details(text)
    user_participant_map[user_id] = parsed.get("participants",[])
    creds = load_dummy_credentials()
    busy  = get_user_busy_times(creds)
    slots = get_available_slots(busy,slot_minutes=parsed.get("duration_minutes",30))
    buttons = build_slot_buttons(slots)
    payload={
        "response_type":"ephemeral",
        "blocks":[
            {"type":"section","text":{"type":"mrkdwn",
             "text":f"*Hi {user_name}, choose a time:*"}},
            {"type":"actions","elements":buttons}
        ]
    }
    async with httpx.AsyncClient() as client:
        await client.post(response_url,json=payload)

async def handle_meeting_interaction(payload):
    val   = payload["actions"][0]["value"]
    user  = payload["user"]["username"]
    uid   = payload["user"]["id"]
    creds = load_dummy_credentials()
    parts= user_participant_map.get(uid,[])
    emails=[name_to_email[n.lower()] for n in parts if n.lower() in name_to_email]
    event=create_calendar_event(
        start_time_iso=val,
        credentials=creds,
        summary=f"Meeting by {user}",
        attendees_emails=emails
    )
    utc_dt = datetime.fromisoformat(event["start"]["dateTime"].replace("Z","+00:00"))
    when   = utc_dt.astimezone(local_tz).strftime("%a %d %b, %I:%M %p")
    blocks=[
        {"type":"section","text":{"type":"mrkdwn",
         "text":f"✅ *{user}, booked!* 🕒 `{when}`"}},
        {"type":"actions","elements":[
            {"type":"button","text":{"type":"plain_text","text":"🔗 View"},
             "url":event["htmlLink"]}
        ]}
    ]
    return JSONResponse({"response_type":"ephemeral",
                         "replace_original":True,"blocks":blocks})
