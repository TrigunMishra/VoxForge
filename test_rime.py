import os

import requests
from dotenv import load_dotenv

load_dotenv()

RIME_API_KEY = os.getenv("RIME_API_KEY")
TEXT = "Welcome to JSS Noida, I can help you find your way around campus"

url = "https://users.rime.ai/v1/rime-tts"
headers = {
    "Authorization": f"Bearer {RIME_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}

# Change "speaker" (e.g. "astra", "celeste") or "language" (e.g. "hi", "fr") here.
payload = {
    "text": TEXT,
    "speaker": "celeste",
    "modelId": "coda",
    "language": "en",
}

response = requests.post(url, headers=headers, json=payload)
response.raise_for_status()

with open("test_output.mp3", "wb") as f:
    f.write(response.content)

print("Success! Audio saved to test_output.mp3")
