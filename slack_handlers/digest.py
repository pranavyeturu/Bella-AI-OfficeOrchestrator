# slack_handlers/digest.py
import os, json
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from slack_utils.client import slack_client
from parser.chat_digest import classify_messages, assemble_digest
from slack_sdk.errors import SlackApiError

async def handle_summarise_command(channel_id: str, user_id: str):

    try:
        slack_client.conversations_join(channel=channel_id)
    except SlackApiError as e:
        if e.response["error"] not in ("method_not_supported_for_channel","already_in_channel"):
            # only ignore “already_in_channel” or unsupported (e.g. private) errors
            raise
    
    # 1) pull last N messages (say 100) from the channel
    history = slack_client.conversations_history(
        channel=channel_id, limit=100
    ).get("messages", [])
    # filter out bots, threads, your own invitations...
    msgs = [{"text":m["text"]} for m in history if "subtype" not in m]

    # 2) classify + assemble
    annotations = classify_messages(msgs)
    # merge back text + priority
    for ann in annotations:
        idx = ann["index"]-1
        msgs[idx]["priority"] = ann["priority"]
    digest = assemble_digest(msgs)

    # 3) build a Block Kit DM
    blocks = []
    for section, lines in [
        ("*Highlights (incidents)*", digest["incident"]),
        ("*Actions (deadlines)*", digest["deadline"]),
        ("*FYI*"          , digest["FYI"])
    ]:
        if lines:
            blocks.append({"type":"section","text":{"type":"mrkdwn","text":section}})
            for txt in lines:
                blocks.append({"type":"section","text":{"type":"mrkdwn","text":"• "+txt}})
            blocks.append({"type":"divider"})
    if blocks and blocks[-1]["type"]=="divider":
        blocks.pop()

    # 4) DM back to the invoking user
    slack_client.chat_postMessage(
        channel=user_id,
        text="Here’s your channel digest:",
        blocks=blocks
    )

    try:
        # this is the line that was blowing up
        slack_client.chat_postMessage(
            channel=channel_id,
            text="Here’s your digest!",
            blocks=blocks,        # or attachments=…
        )
    except SlackApiError as e:
        # swallow only that specific JSON-error
        err = e.response.get("error", "")
        if "src property must be a valid json object" in err:
            print("Check Slack Chats for Channel Digest", e)
        else:
            # re-raise anything else we didn’t expect
            raise
    return JSONResponse(status_code=200, content={})

async def handle_channel_monitor(event: dict):
    """
    Called on message events.  Keep a sliding window count in e.g. Redis.
    When > 100 messages in 8h, fire handle_summarise_command.
    """
    channel = event["channel"]
    # increment in Redis, check TTL...
    from utils.redis_client import redis
    ts = int(event["ts"].split(".")[0])
    redis.zadd(f"msgs:{channel}", {ts:ts})
    # remove entries older than 8h
    cutoff = ts - 8*3600
    redis.zremrangebyscore(f"msgs:{channel}", 0, cutoff)
    count = redis.zcard(f"msgs:{channel}")
    if count > 100:
        # find most active user? Or DM channel owner?
        owner = os.getenv("CHANNEL_MONITOR_USER")
        await handle_summarise_command(channel, owner)
