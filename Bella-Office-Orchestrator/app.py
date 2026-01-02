import os, traceback, pytz, pandas as pd, streamlit as st
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
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
except Exception as e:
    st.error(f"NLP commands API not found: {e}. NLP automation features will not work.")
    classify_intent = lambda *_, **__: ""
    get_free_slots_nlp = schedule_meeting_nlp = run_logtask_nlp = run_sendreport_nlp = lambda *_, **__: None
    run_summarise_nlp = run_assign_ticket_nlp = run_resolve_ticket_nlp = lambda *_, **__: None

try:
    from workflows import onboarding, offboarding, preprocess_llm, db_refresh, office_ops_llm
    from tools import db_tools
except Exception:
    onboarding = offboarding = preprocess_llm = db_refresh = office_ops_llm = None
    from types import SimpleNamespace
    db_tools = SimpleNamespace(PG_CONN=None)

try:
    from modules.pr_reviewer import PRReviewer
    from modules.cicd_deployer import CICDDeployer
    from modules.release_notes import ReleaseNotes
    from modules.data_refresh import DataRefresh
except Exception:
    PRReviewer = CICDDeployer = ReleaseNotes = DataRefresh = lambda *_, **__: None

IST = pytz.timezone("Asia/Kolkata")

def format_slot(s):
    start = datetime.fromisoformat(s["start"]).astimezone(IST)
    end = datetime.fromisoformat(s["end"]).astimezone(IST)
    return f"{start.strftime('%a %b %d • %I:%M %p')} – {end.strftime('%I:%M %p')} IST"

def load_google_credentials(pkl_path="user_creds.pkl"):
    import pickle
    try:
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        st.error("Google Calendar credentials not found. Visit /google/login in your FastAPI app, authorize and retry.")
        st.text(str(e))
        st.stop()

if "page" not in st.session_state:
    st.session_state.page = "home"
if "refresh_table" not in st.session_state:
    st.session_state.refresh_table = None

def intro_page():
    st.set_page_config(page_title="Bella • Office Assistant", layout="centered")
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        background-color: #15161a !important;
        font-family: monospace !important;
        color: #faf8fc !important;
    }
    .bella-card {
        background: #23222b;
        border-radius: 18px;
        box-shadow: 0 6px 36px 0 rgba(0,0,0,0.25), 0 1.5px 8px 0 #2222;
        padding: 2.4rem 2.4rem 2.0rem 2.4rem;
        max-width: 680px;
        margin-left: auto;
        margin-right: auto;
        margin-top: 3.6rem;
        margin-bottom: 2.4rem;
        border: 1.3px solid #28223a;
        position: relative;
        overflow: visible;
    }
    .bella-title {
        font-size: 2.6rem;
        font-weight: 900;
        letter-spacing: 1.5px;
        color: #f8ecfd;
        margin-bottom: 0.65rem;
        display: flex;
        align-items: center;
        line-height: 1.15;
        text-shadow: 0 2px 8px #8446c662, 0 1px 0 #2e1625;
    }
    .bella-icon {
        font-size: 2.1rem;
        margin-right: 0.9rem;
        color: #ffe46d;
        margin-top: -5px;
        filter: drop-shadow(0 2px 6px #fffdbe65);
    }
    .bella-subtitle {
        font-size: 1.22rem;
        font-weight: 700;
        color: #c8aedb;
        margin-bottom: 1.12rem;
        letter-spacing: 0.01em;
    }
    .bella-desc {
        font-size: 1.14rem;
        color: #fffaee;
        margin-bottom: 1.1rem;
        margin-top: 0.16rem;
        line-height: 1.7;
        background: #382843;
        border-radius: 12px;
        padding: 1.05rem 1.55rem 1.05rem 1.55rem;
        border-left: 4px solid #c792e9;
        box-shadow: 0 1.5px 7px #1a152232;
    }
    .bella-bold {
        font-weight: 900;
        color: #ffe46d;
        background: #28283a;
        border-radius: 8px;
        padding: 0.7rem 1.1rem;
        display: inline-block;
        margin-top: 1.09rem;
        margin-bottom: 0.3rem;
        font-size: 1.13rem;
        letter-spacing: 0.01em;
        box-shadow: 0 1.5px 4px #2b1e3e56;
    }
    .bella-integration-list {
        display: flex;
        flex-wrap: wrap;
        gap: 2.1rem 1.35rem;
        justify-content: flex-start;
        margin-top: 1.1rem;
        margin-bottom: 1.1rem;
    }
    .integration-item {
        font-size: 1.10rem;
        color: #1c143a;
        background: #fffbe9;
        border-radius: 10px;
        padding: 0.57rem 1.40rem;
        margin-bottom: 0.39rem;
        border: 2px solid #f7e1f8;
        font-weight: 800;
        box-shadow: 0 1px 7px #0002;
        transition: transform 0.12s, box-shadow 0.15s;
    }
    .integration-item:hover {
        background: #ffe46d;
        color: #120624;
        transform: scale(1.04);
        box-shadow: 0 2.5px 15px #ffe46d88, 0 2px 6px #2222;
        cursor: pointer;
    }
    .bella-btn-main {
        background: #9114e0;
        color: #1e062a;
        border: none;
        border-radius: 10px;
        padding: 0.9em 2.6em;
        font-size: 1.22rem;
        font-weight: 900;
        margin-top: 28px;
        margin-bottom: 3px;
        box-shadow: 0 3px 14px 0 #c793e962, 0 1.2px 6px #110a1848;
        cursor: pointer;
        transition: transform 0.13s, box-shadow 0.19s, background 0.17s;
        outline: none;
        letter-spacing: 0.01em;
        text-shadow: 0 1.5px 8px #fff1, 0 1px 0 #fffb;
    }
    .bella-btn-main:hover {
        background: linear-gradient(92deg, #f7971e, #b16cea 90%);
        color: #1e062a;
        transform: scale(1.055) translateY(-1.2px);
        box-shadow: 0 10px 32px 0 #fcbb4488, 0 3px 13px #4422;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="bella-card">', unsafe_allow_html=True)
    st.markdown('<div class="bella-title"><span class="bella-icon">📁</span>Meet Bella, your AI Orchestrator</div>', unsafe_allow_html=True)
    st.markdown('<div class="bella-subtitle">One assistant, twelve powerful workflows</div>', unsafe_allow_html=True)
    st.markdown('<div class="bella-desc"><b>Bella handles the repetitive stuff, so your team can focus on real work.</b><br><br>Just type your request in plain English—Bella picks the right workflow and gets it done.</div>', unsafe_allow_html=True)
    st.markdown('<div class="bella-bold">Integrates with your favorite tools:</div>', unsafe_allow_html=True)
    integrations = ["Slack","Jira","Okta","Git","GitHub","Google Calendar","HubSpot"]
    st.markdown('<div class="bella-integration-list">' + "".join(f'<div class="integration-item">{x}</div>' for x in integrations) + '</div>', unsafe_allow_html=True)
    if st.button("Try Bella", key="try_bella"):
        st.session_state.page = "main"
        st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def run_nlp_flow(nl, user_id):
    intent = classify_intent(nl)
    if intent == "schedule_meeting":
        from parser.gpt_parser import extract_meeting_details
        details = extract_meeting_details(nl)
        duration = details.get("duration_minutes")
        tf = details.get("timeframe")
        participants = details.get("participants", [])
        if not duration or not tf or not participants:
            st.error("Parser failed to extract duration, participants or timeframe")
            st.stop()
        st.markdown(f"**Duration:** {duration} minutes")
        st.markdown(f"**Participants:** {', '.join(participants)}")
        st.markdown(f"**Window:** {tf['start']} → {tf['end']} (ISO)")
        creds = load_google_credentials()
        from parser.google_calendar import get_user_busy_times, get_available_slots
        busy = get_user_busy_times(creds)
        start_win = datetime.fromisoformat(tf["start"])
        end_win = datetime.fromisoformat(tf["end"])
        if start_win.tzinfo is None:
            start_win = IST.localize(start_win)
        if end_win.tzinfo is None:
            end_win = IST.localize(end_win)
        slots = get_available_slots(busy_times=busy, start_day=start_win, end_day=end_win, slot_minutes=duration)
        if not slots:
            st.warning("No free slots found")
            st.stop()
        st.session_state.meeting_options = [format_slot(s) for s in slots[:5]]
        st.session_state.meeting_slots = slots[:5]
        st.session_state.meeting_details = details
        return
    if intent == "log_task":
        st.success(f"Logged task → {run_logtask_nlp(nl, user_id)}")
    elif intent == "send_report":
        run_sendreport_nlp()
        st.success("Weekly report sent")
    elif intent == "summarise_chat":
        st.json(run_summarise_nlp(nl, user_id))
    elif intent == "assign_ticket":
        st.success(f"Assigned ticket → {run_assign_ticket_nlp(nl)}")
    elif intent == "resolve_ticket":
        st.success(f"Resolved ticket → {run_resolve_ticket_nlp(nl, user_id)}")
    elif "onboard" in nl.lower():
        st.info("I’ll need the new hire’s first name, last name, and email.")
        with st.form("onboard_form"):
            first = st.text_input("First name")
            last = st.text_input("Last name")
            email = st.text_input("Work email")
            if st.form_submit_button("Run onboarding") and onboarding:
                onboarding.run(first, last, email, st.write)
    elif "offboard" in nl.lower():
        st.info("I’ll need the departing employee’s email.")
        with st.form("offboard_form"):
            email = st.text_input("Work email")
            if st.form_submit_button("Run off-boarding") and offboarding:
                offboarding.run(email, st.write)
    elif "preprocess" in nl.lower() and preprocess_llm:
        preprocess_llm.run_nlp(nl, st.write)
    elif "refresh" in nl.lower():
        st.info("Enter a table name to refresh, or leave blank to refresh the whole DB.")
        if st.session_state.refresh_table is None:
            with st.form("refresh_form"):
                tbl = st.text_input("Table name (optional)")
                if st.form_submit_button("Start refresh"):
                    st.session_state.refresh_table = tbl or None
        if st.session_state.refresh_table is not None and db_refresh:
            db_refresh.run(st.write, st.session_state.refresh_table)
            if st.button("Clear refresh state"):
                st.session_state.refresh_table = None
    elif "office summary" in nl.lower() or "eod report" in nl.lower():
        if office_ops_llm and st.button("Run End-of-Day Office Summary"):
            office_ops_llm.run_daily_summary(logger=st.write)
    else:
        st.warning("Command not supported")

def main_page():
    st.title("AI Orchestrator – Bella")
    st.subheader("Streamlining business operations")
    with st.form("nlp_form"):
        nl = st.text_input(label="", placeholder="Ask me to run a workflow…", label_visibility="collapsed")
        submitted = st.form_submit_button("Run")
    if submitted and nl.strip():
        needs_id = classify_intent(nl) in {"log_task", "summarise_chat", "resolve_ticket"}
        user_id = st.session_state.get("slack_user_id", "")
        if needs_id and not user_id:
            user_id = st.text_input("This command requires your Slack User ID", key="slack_user_id_input")
            if st.button("Save ID") and user_id:
                st.session_state.slack_user_id = user_id
                st.experimental_rerun()
            st.stop()
        run_nlp_flow(nl, user_id)
    if "meeting_options" in st.session_state and "meeting_slots" in st.session_state:
        choice = st.selectbox("Choose a slot to book", st.session_state.meeting_options)
        if st.button("Schedule Meeting"):
            idx = st.session_state.meeting_options.index(choice)
            iso = st.session_state.meeting_slots[idx]["start"]
            creds = load_google_credentials()
            from parser.google_calendar import create_calendar_event
            event = create_calendar_event(
                start_time_iso=iso,
                credentials=creds,
                summary=f"Meeting via NLP: {', '.join(st.session_state.meeting_details['participants'])}",
                attendees_emails=[],
                timezone="Asia/Kolkata",
            )
            link = event.get("htmlLink")
            when = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(IST).strftime("%a %b %d • %I:%M %p")
            st.success(f"Meeting booked for **{when} IST**  [Open]({link})")
    if db_tools.PG_CONN:
        try:
            ddl = pd.read_sql(
                """
                SELECT table_schema||'.'||table_name AS tbl,
                       string_agg(column_name||' '||data_type, ', ') AS cols
                FROM information_schema.columns
                GROUP BY 1
                LIMIT 20
                """,
                db_tools.PG_CONN,
            ).to_string(index=False)
            st.expander("Database DDL snapshot (top 20 tables)").write(ddl)
        except Exception:
            pass
    if st.button("Back to Home"):
        st.session_state.page = "home"
        st.experimental_rerun()

if st.session_state.page == "home":
    intro_page()
else:
    main_page()
