# parser/chat_digest.py
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_messages(messages: list[dict]) -> list[dict]:
    """
    Given a list of Slack message dicts, call the LLM to tag each
    as one of: "deadline", "incident", or "FYI".
    Returns messages annotated with {"priority": ...}.
    """
    text = "\n".join(f"{i+1}. {m['text']}" for i,m in enumerate(messages))
    prompt = (
        "You are a triage assistant. Given these Slack messages:\n"
        f"{text}\n\n"
        "Return JSON array of objects [{index:int, priority:str}],\n"
        "where priority ∈ {\"deadline\",\"incident\",\"FYI\"}."
    )
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.0,
        messages=[{"role":"user","content":prompt}]
    )
    out = resp.choices[0].message.content
    # e.g. '[{"index":1,"priority":"FYI"},...]'
    return eval(out)

def assemble_digest(messages: list[dict]) -> dict:
    """
    Given annotated messages, build three sections:
      • Highlights (incident)
      • Actions (deadline)
      • FYI (all FYI)
    Returns a dict {highlights:[...], actions:[...], fyi:[...]}.
    """
    by_priority = {"incident":[], "deadline":[], "FYI":[]}
    for m in messages:
        p = m.get("priority","FYI")
        by_priority[p].append(m["text"])
    return by_priority
