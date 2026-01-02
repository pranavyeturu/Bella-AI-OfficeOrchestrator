# ai_utils.py

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def summarize_overdue_tasks(tasks, user_name):
    bullets = "\n".join(f"- {i['key']}: {i['fields']['summary']}" for i in tasks)
    prompt = (
        f"You are a friendly reminder bot. Write a Slack message to {user_name}:\n"
        f"Overdue tasks:\n{bullets}\n"
        "Encourage logging time or marking done, under 50 words."
    )
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.5,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()

def draft_weekly_report(df):
    """
    Synchronous summary generator—no asyncio needed.
    Expects df with columns: user_name, total_minutes, frequency.
    """
    
    rows = "\n".join(
        f"{r.user_name}: {r.total_minutes}h over {r.frequency} entries"
        for r in df.itertuples()
    )
    prompt = (
        "You are an executive assistant. Here is this week's time-log summary:\n"
        f"{rows}\n"
        "Write a concise, 3-sentence report highlighting each person's activity."
    )
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.3,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()
