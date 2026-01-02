# streamlit_app.py

import streamlit as st
from datetime import datetime
import traceback
import pytz

from commands_api import (
    classify_intent,
    get_free_slots_nlp,
    schedule_meeting_nlp,
    run_logtask_nlp,
    run_sendreport_nlp,
    run_summarise_nlp,
    run_assign_ticket_nlp,
    run_resolve_ticket_nlp,
)

IST = pytz.timezone("Asia/Kolkata")

def format_slot(s):
    start = datetime.fromisoformat(s["start"]).astimezone(IST)
    end = datetime.fromisoformat(s["end"]).astimezone(IST)
    return f"{start.strftime('%a %b %d • %I:%M %p')} – {end.strftime('%I:%M %p')} IST"

def load_google_credentials(pkl_path="user_creds.pkl"):
    """Loads OAuth credentials saved via /google/login."""
    import pickle
    try:
        with open(pkl_path, "rb") as f:
            creds = pickle.load(f)
        return creds
    except Exception as e:
        st.error("❗ Google Calendar credentials not found. Please visit `/google/login` in your FastAPI app, authorize, and retry.")
        st.text(str(e))
        st.stop()

st.set_page_config(page_title="🗣️ All-NLP Command Center", layout="centered")
st.title("✨ Your Six NLP-Driven Automations")

# 1) Ask for Slack user ID up front
user_id = st.text_input("🔑 Your Slack User ID", "")
if not user_id:
    st.info("ℹ️ Please enter your Slack user ID to enable certain commands.")

# 2) Single NL input box
nl = st.text_area(
    "💬 Enter any command in plain English:",
    placeholder=(
        "e.g. “Book 30 mins with Alex & Priya tomorrow morning”,\n"
        "“Log 45 to SCRUM-123”, “Send weekly report”,\n"
        "“Summarise channel C09020HKRLP”,\n"
        "“Assign urgent ticket HD-512 about login failures”,\n"
        "“Resolved HD-512”"
    ),
    height=120,
)

# 3) Parse/classify/run on "Run" button
if st.button("Run"):
    if not nl.strip():
        st.error("❗ Please type a command before hitting Run.")
    else:
        with st.spinner("👉 Classifying your command…"):
            intent = classify_intent(nl)

        try:
            # ─── schedule_meeting ──────────────────────────────
            if intent == "schedule_meeting":
                with st.spinner("⚙️ Parsing your request..."):
                    from parser.gpt_parser import extract_meeting_details
                    try:
                        details = extract_meeting_details(nl)
                    except Exception as e:
                        st.error(f"❗ Could not parse meeting details: {e}")
                        st.text(traceback.format_exc())
                        st.stop()

                duration = details.get("duration_minutes")
                tf = details.get("timeframe")
                participants = details.get("participants", [])
                if not duration or not tf or not participants:
                    st.error("❗ Parser failed to extract duration, participants, or timeframe.")
                    st.json(details)
                    st.stop()

                st.markdown(f"**Duration:** {duration} minutes")
                st.markdown(f"**Participants:** {', '.join(participants)}")
                st.markdown(f"**Window:** {tf['start']} → {tf['end']} (ISO)")

                creds = load_google_credentials()
                from parser.google_calendar import get_user_busy_times, get_available_slots
                busy = get_user_busy_times(creds)
                try:
                    start_win = datetime.fromisoformat(tf["start"])
                    if start_win.tzinfo is None:
                        start_win = IST.localize(start_win)
                    end_win = datetime.fromisoformat(tf["end"])
                    if end_win.tzinfo is None:
                        end_win = IST.localize(end_win)
                except Exception as e:
                    st.error(f"❗ Invalid timeframe format: {e}")
                    st.stop()

                with st.spinner("🔍 Searching for free slots..."):
                    slots = get_available_slots(
                        busy_times=busy,
                        start_day=start_win,
                        end_day=end_win,
                        slot_minutes=duration
                    )
                if not slots:
                    st.warning("🤔 No free slots found in your window.")
                    st.stop()

                # Save everything in session_state for next rerun!
                st.session_state['meeting_options'] = [format_slot(s) for s in slots[:5]]
                st.session_state['meeting_slots'] = slots[:5]
                st.session_state['meeting_details'] = details

            # ─── log_task ─────────────────────────────────────
            elif intent == "log_task":
                if not user_id:
                    st.error("🚫 You must enter your Slack user ID above.")
                else:
                    res = run_logtask_nlp(nl, user_id)
                    st.success(f"✅ Logged task → {res}")

            # ─── send_report ────────────────────────────────
            elif intent == "send_report":
                _ = run_sendreport_nlp()
                st.success("📧 Weekly report sent!")

            # ─── summarise_chat ─────────────────────────────
            elif intent == "summarise_chat":
                if not user_id:
                    st.error("🚫 You must enter your Slack user ID above.")
                else:
                    res = run_summarise_nlp(nl, user_id)
                    st.json(res)

            # ─── assign_ticket ──────────────────────────────
            elif intent == "assign_ticket":
                res = run_assign_ticket_nlp(nl)
                st.success(f"✅ Assigned ticket → {res}")

            # ─── resolve_ticket ─────────────────────────────
            elif intent == "resolve_ticket":
                if not user_id:
                    st.error("🚫 You must enter your Slack user ID above.")
                else:
                    res = run_resolve_ticket_nlp(nl, user_id)
                    st.success(f"✅ Resolved ticket → {res}")

            else:
                st.warning(f"❓ Could not map intent: `{intent}`")

        except Exception as e:
            st.error(f"⚠️ Error during `{intent}`: {e}")
            st.text(traceback.format_exc())

# --- Always show the slot dropdown and booking button if slots are available ---
if 'meeting_options' in st.session_state and 'meeting_slots' in st.session_state:
    choice = st.selectbox("Choose a slot to book:", st.session_state['meeting_options'])
    if st.button("Schedule Meeting"):
        options = st.session_state['meeting_options']
        slots = st.session_state['meeting_slots']
        details = st.session_state['meeting_details']
        creds = load_google_credentials()
        from parser.google_calendar import create_calendar_event
        idx = options.index(choice)
        iso = slots[idx]["start"]
        st.write(f"DEBUG: Booking meeting at {iso}")
        with st.spinner("⏳ Booking in Google Calendar..."):
            try:
                event = create_calendar_event(
                    start_time_iso=iso,
                    credentials=creds,
                    summary=f"Meeting via NLP: {', '.join(details['participants'])}",
                    attendees_emails=[],
                    timezone="Asia/Kolkata"
                )
                st.write(event)  # DEBUG: Print the event dict!
                link = event.get("htmlLink")
                when = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(IST).strftime("%a %b %d • %I:%M %p")
                st.success(f"🎉 Meeting booked for **{when} IST**! [Open in Calendar]({link})")
                # Optionally reset session state after booking:
                # for k in ['meeting_options','meeting_slots','meeting_details']:
                #     st.session_state.pop(k, None)
            except Exception as e:
                st.error(f"❗ Could not book meeting: {e}")
                st.text(traceback.format_exc())
