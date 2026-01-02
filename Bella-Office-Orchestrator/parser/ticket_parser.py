# parser/ticket_parser.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_ticket_details(prompt: str) -> dict:
    """
    Ask the LLM to pull out:
      - ticket_id  (e.g. 'HD-512')
      - urgency    (e.g. 'urgent', 'high', etc.)
      - subject    (short description)
      - link       (URL)
    from the user's natural-language request.
    Returns a dict with exactly those four keys.
    """
    system = (
      "You are a ticket-parsing assistant.  "
      "Given a user message, extract exactly four fields in JSON:\n"
      "  • ticket_id  (e.g. 'HD-512')\n"
      "  • urgency    (e.g. 'urgent')\n"
      "  • subject    (short description of the problem)\n"
      "  • link       (a URL to the ticket)\n\n"
      "Respond *only* with JSON, e.g.: "
      "{\"ticket_id\":\"HD-512\",\"urgency\":\"urgent\","
      "\"subject\":\"login failures\",\"link\":\"https://…\"}"
    )
    resp = llm.chat.completions.create(
      model="gpt-3.5-turbo",
      temperature=0.0,
      messages=[
        {"role":"system", "content": system},
        {"role":"user",   "content": prompt}
      ]
    )
    # parse and return
    return json.loads(resp.choices[0].message.content)
