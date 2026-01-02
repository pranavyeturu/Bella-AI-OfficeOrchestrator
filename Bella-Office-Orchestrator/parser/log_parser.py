import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_log_details(prompt: str) -> dict:
    """
    Input: "Scrum-123 45"
    Output: {"issue": "SCRUM-123", "minutes":45}
    """
    system = (
      "You are a parser that extracts a Jira issue key "
      "and integer minutes from a short command. "
      "Respond *only* with JSON: {\"issue\":..., \"minutes\":...}."
    )
    resp = llm.chat.completions.create(
      model="gpt-3.5-turbo",
      temperature=0.0,
      messages=[
        {"role":"system","content": system},
        {"role":"user",  "content": prompt}
      ]
    )
    content = resp.choices[0].message.content
    try:
        return eval(content)
    except:
        raise ValueError(f"Could not parse log command: {content}")
