import os, base64, json, requests
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()
SITE   = os.getenv("JIRA_SITE")            # https://harshadayini.atlassian.net
EMAIL  = os.getenv("JIRA_EMAIL")
TOKEN  = os.getenv("JIRA_API_TOKEN")
PROJECT = os.getenv("JIRA_PROJECT_KEY", "DO3")   # <-- update to your new key

auth = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEAD = {
    "Authorization": f"Basic {auth}",
    "Accept":        "application/json",
    "Content-Type":  "application/json",
}



@lru_cache
def component_id(name: str) -> str:
    url = f"{SITE}/rest/api/3/project/{PROJECT}/components"
    comps = requests.get(url, headers=HEAD).json()
    for c in comps:
        if c["name"].lower() == name.lower():
            return c["id"]
    raise ValueError(f"No component named {name} in project {PROJECT}")


def create_and_close_task(dept: str, summary: str):
    """Create a task tagged with a component, then transition to Done."""
    comp_id = component_id(dept)   # dept = IT / Security / HR / Facilities i made these components in slack
    payload = {
        "fields": {
            "project":    {"key": PROJECT},
            "summary":    summary,
            "issuetype":  {"name": "Task"},
            "components": [{"id": comp_id}]
        }
    }
    response = requests.post(f"{SITE}/rest/api/3/issue", headers=HEAD, json=payload)
    data = response.json()

    # Debug print
    if "key" not in data:
        print("❌ Jira issue creation failed:", data)

    r = requests.post(f"{SITE}/rest/api/3/issue", headers=HEAD, json=payload)

    if r.status_code >= 300:
        # Show the full error response before breaking
        print("❌ Jira issue creation failed:", r.json())
        raise RuntimeError("Jira issue creation failed.")

    data = r.json()
    
    issue = data["key"]  # This will now only fail if something really breaks

    # 2. move to Done
    trans = requests.get(f"{SITE}/rest/api/3/issue/{issue}/transitions",
                         headers=HEAD).json()["transitions"]
    done_id = next(t["id"] for t in trans if t["to"]["name"] == "Done")
    requests.post(f"{SITE}/rest/api/3/issue/{issue}/transitions",
                  headers=HEAD, json={"transition": {"id": done_id}})
    return issue
