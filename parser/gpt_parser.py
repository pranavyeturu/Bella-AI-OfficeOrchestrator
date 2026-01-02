import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import json

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_meeting_details(prompt: str) -> dict:
    system_prompt = (
        "You are a scheduling assistant.  From the user’s request, extract **JSON** with these keys:\n"
        "  • duration_minutes (integer)\n"
        "  • participants (list of names)\n"
        "  • timeframe: an object with “start” and “end” in ISO 8601 (local time) indicating the allowed window.\n\n"
        "For example, for “Book 30 mins with Alex tomorrow between 2 PM and 4 PM,” you might return:\n"
        "{\n"
        "  \"duration_minutes\": 30,\n"
        "  \"participants\": [\"Alex\"],\n"
        "  \"timeframe\": {\n"
        "    \"start\": \"2025-06-16T14:00:00\",\n"
        "    \"end\":   \"2025-06-16T16:00:00\"\n"
        "  }\n"
        "}\n\n"
        "Respond with **only** the JSON object."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.0,
        messages=[
            {"role":"system", "content": system_prompt},
            {"role":"user",   "content": prompt}
        ]
    )
    return json.loads(response.choices[0].message.content)

