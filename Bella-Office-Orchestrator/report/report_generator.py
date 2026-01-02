# report/report_generator.py

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
from fpdf import FPDF

from jira.jira_api import fetch_user_tasks
from ai_utils import draft_weekly_report
from smtp_utils import send_email_via_smtp
from slack_utils.client import slack_client

from sqlalchemy.orm import Session
from db import SessionLocal
from models import LogEntry

from email_map import USER_ID_TO_EMAIL, USER_ID_TO_NAME  

# Map Slack user IDs to Jira emails (adjust as needed)
SLACK_TO_JIRA = {
    "U12345": "alice@domain.com",
    "U67890": "bob@domain.com",
}


def compile_weekly_data():
    """
    Returns a DataFrame grouped by user_name & user_email,
    with total_minutes and frequency of logs.
    """
    db = SessionLocal()
    entries = db.query(LogEntry).all()
    db.close()

    rows = []
    for e in entries:
        # if you used static map:
        name  = USER_ID_TO_NAME.get(e.user_id, e.user_id)
        email = USER_ID_TO_EMAIL.get(e.user_id)
        # if you used dynamic lookup instead:
        # profile = get_user_profile(e.user_id)
        # name, email = profile['name'], profile['email']

        rows.append({
            "user_name":   name,
            "user_email":  email,
            "issue":       e.issue,
            "minutes":     e.minutes,
            "timestamp":   e.timestamp,
        })

    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["user_name", "user_email"])
          .agg(
            total_minutes=("minutes","sum"),
            frequency=("minutes","count")
          )
          .reset_index()
    )
    return summary

def compile_and_send_weekly_report():
    # 1) Gather data
    df = compile_weekly_data()
    csv_path = "weekly_report.csv"
    pdf_path = "weekly_report.pdf"

    # 2) Write CSV
    df.to_csv(csv_path, index=False)

    # 3) Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Weekly Report - {datetime.utcnow().date()}", ln=1)

    # Now iterate over your summary DataFrame
    for _, row in df.iterrows():
        user = row["user_name"]
        mins = row["total_minutes"]
        freq = row["frequency"]
        pdf.cell(
            0, 8,
            f"{user}: {mins}h logged over {freq} entries",
            ln=1
        )

    pdf.output(pdf_path)

    # 4) Draft human summary
    summary_text = draft_weekly_report(df)

    # 5) Email to manager
    subject = f"Weekly Report — {datetime.utcnow().date()}"
    send_email_via_smtp(
        subject=subject,
        body=summary_text,
        to_addresses=[os.getenv("MANAGER_EMAIL")],
        attachments=[csv_path, pdf_path]
    )

    # 6) Optional: post back to Slack
    mgr_channel = os.getenv("MANAGER_SLACK_CHANNEL")
    if mgr_channel:
        slack_client.chat_postMessage(
            channel=mgr_channel,
            text=summary_text,
            attachments=[{"title":"Weekly CSV","title_link":csv_path}]
        )

    return csv_path, pdf_path