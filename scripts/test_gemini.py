"""
Basic Gemini API connectivity test.

Verifies that the GOOGLE_API_KEY is configured correctly
and that the application can communicate with Gemini.
"""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Add it to your .env file."
    )

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Respond with exactly: IncidentForge Gemini connection successful.",
)

print(response.text)