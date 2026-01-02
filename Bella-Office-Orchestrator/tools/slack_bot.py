import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def post_welcome_message(email: str, channel: str = "#general"):
    """Post a welcome message to Slack (no invite)."""
    message = f"🎉 A new teammate `{email}` has been onboarded! Please welcome them!"
    response = client.chat_postMessage(channel=channel, text=message)
    return response["ts"]  # return timestamp of the message


#offboarding functions::
def post_exit_message(email: str, channel: str = "general"):
    """Announce a departure in Slack."""
    text = f"👋 `{email}` has been off-boarded. Wishing them well!"
    resp = client.chat_postMessage(channel=channel, text=text)
    return resp["ts"]
