# jira/jira_api.py
import os, requests, json
from requests.auth import HTTPBasicAuth
from datetime import datetime

JIRA_URL = os.getenv("JIRA_BASE_URL")
AUTH    = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

def fetch_user_tasks(jira_email):
    jql = f'assignee="{jira_email}" AND statusCategory != Done'
    resp = requests.get(
        f"{JIRA_URL}/rest/api/3/search",
        headers=HEADERS, auth=AUTH,
        params={"jql": jql, "fields": "summary,due,timespent"}
    )
    resp.raise_for_status()
    return resp.json().get("issues", [])

def get_incomplete_tasks(issues):
    today = datetime.utcnow().date()
    out = []
    for issue in issues:
        due = issue["fields"].get("due")
        spent = issue["fields"].get("timespent")
        if due:
            due_date = datetime.fromisoformat(due).date()
            if due_date < today and not spent:
                out.append(issue)
    return out

def mark_done(issue_key):
    payload = {"transition": {"id": "31"}}  # adjust transition ID if needed
    resp = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        headers=HEADERS, auth=AUTH,
        data=json.dumps(payload)
    )
    return resp

def add_worklog(issue_key, minutes, comment="Logged via Slack"):
    payload = {
        "timeSpentSeconds": minutes * 60,
        "comment": {
            "type": "doc", "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ]
        }
    }
    resp = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/worklog",
        headers=HEADERS, auth=AUTH,
        data=json.dumps(payload)
    )
    return resp
