import os
import json
import openai
from tools.db_tools import get_table_catalog

# 1) Load your OpenAI key
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2) Pre-fetch a lightweight schema catalog for the LLM
CATALOG = get_table_catalog(limit=200)

# 3) System prompt describing the JSON format
SYSTEM_PROMPT = """
You are a data work-assistant. Given the table catalog below and a user request,
output exactly one JSON object with these keys:
{
  "mode": "upload" | "query",
  "sql": "...",                 # only if mode == "query"
  "dangerous": true | false,    # true if SQL writes or drops data
  "ask": "..."                  # a follow-up question if you need more info
}
Use only read-only SQL (SELECT/COPY). Any other verb must set "dangerous": true.
"""

def plan(request_text: str) -> dict:
    """Generate a tool plan given a natural-language request."""
    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": f"CATALOG:\n{CATALOG}\n\nREQUEST:\n{request_text}"},
    ]

    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"}  # force pure JSON response
    )

    return json.loads(resp.choices[0].message.content)
