# VoxForge

ScrapWorks' submission to the Starforge hackathon

A voice-powered campus guide: speak a question, get a spoken answer. Built with Python + Gradio, using Google AI (transcription + LLM), Qdrant (vector search), and Rime (text-to-speech).

## Tools used

- Python 3.11
- Gradio (web UI)
- Google AI Studio — Gemini 3.1 Flash Lite (transcription), Gemma 4 26B (answer phrasing)
- Qdrant Cloud — vector database
- Rime Coda — text-to-speech
- fastembed — embeddings
- python-dotenv, requests, pydub

## APIs you need to sign up for

| Service | What for | Where to sign up |
| --- | --- | --- |
| Google AI Studio | Transcription + LLM | https://aistudio.google.com (free tier) |
| Qdrant Cloud | Vector database | https://cloud.qdrant.io (free tier) |
| Rime | Text-to-speech | https://app.rime.ai (free credits) |

## Setup

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Add your API keys
cp .env.example .env
# then edit .env with your QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY, RIME_API_KEY

# 3. Fill the vector database with the FAQ (one time)
.venv/bin/python setup_qdrant.py

# 4. Run the web app
.venv/bin/python app.py
```

Open the URL printed in the terminal (default http://127.0.0.1:7860), press the mic, and ask a question.

## Other scripts

- `pipeline.py` — answer a question from the command line (no UI)
- `test_search.py` — test the Qdrant search
- `test_rime.py` — test Rime TTS
- `faq_data.json` — the FAQ knowledge base (edit to add your own Q&As, then re-run `setup_qdrant.py`)

For a full project walkthrough, see `INFO.md`.
