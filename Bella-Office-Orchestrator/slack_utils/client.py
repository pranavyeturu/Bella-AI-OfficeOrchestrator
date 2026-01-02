import os
from slack_sdk import WebClient

slack_token = os.getenv("SLACK_BOT_TOKEN")
if not slack_token:
    raise RuntimeError("Missing SLACK_BOT_TOKEN in .env")

slack_client = WebClient(token=slack_token)