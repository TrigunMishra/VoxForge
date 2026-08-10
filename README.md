# Voice of Campus

A voice-first campus assistant that answers student questions **out loud** — in English or Hindi — from a conversational kiosk UI.

Press the mic, ask anything about campus life, and hear a natural spoken answer. Follow-ups, compound questions, Hindi/Hinglish, and even Devanagari input all just work.

Built in Python with a fast RAG pipeline: **Gemini** for speech-to-text and answer phrasing, **Qdrant + fastembed** for semantic FAQ retrieval, and **Rime Coda** for lifelike text-to-speech.

---

## Highlights

- **End-to-end voice loop** — the user speaks, the assistant speaks back. No typing required.
- **Automatic bilingual support** — detects English vs Hindi/Hinglish/Devanagari per question, answers in the same language, and switches the TTS voice (Hindi voice for Hindi, English voice for English). Hindi answers are generated in Devanagari script.
- **Semantic FAQ retrieval (RAG)** — 70 FAQs expanded into **288 natural-phrase variants**, embedded with `fastembed` and searched with cosine similarity in **Qdrant Cloud**, so rephrased questions still match.
- **Compound & multi-part questions** — "where is the library and what are the mess timings?" is answered in full by retrieving and reasoning over several FAQ entries at once.
- **Continuous conversation** — a rolling conversation context (last 3 turns) lets users ask follow-ups like "what about on weekends?" without repeating themselves.
- **Honest fallbacks** — when no FAQ entry matches, the assistant says so gracefully instead of hallucinating, and the UI shows *why*.
- **Kiosk-grade UI** — a big, centered mic as the focal point, a live pulsing status indicator (Listening / Thinking / Speaking), per-turn **EN/HI** language tags, and green "Matched · 94% similarity" or amber "No strong match" badges under every answer.
- **Fast** — a 20x cut in answer-generation latency by switching to a smaller, faster LLM (see [Performance](#performance)).

---

## How it works

```
        ┌────────────┐   audio   ┌───────────────────┐   text   ┌───────────────────┐
   You  │   Mic      │ ────────► │  Gemini Flash Lite │ ───────► │  fastembed (BGE)  │
        └────────────┘           │  speech-to-text    │          └────────┬──────────┘
            ▲                    └───────────────────┘                   │ embedding
            │ audio                                                        ▼
        ┌───┴──────────┐   text   ┌───────────────────┐   top FAQs   ┌────────────┐
        │ Rime Coda TTS│ ◄─────── │  Gemini Flash Lite│ ◄─────────── │  Qdrant    │
        │ (hi/en voice)│  answer  │  answer phrasing  │   (≤ 4)      │  vector DB │
        └──────────────┘          └───────────────────┘               └────────────┘
```

1. **Transcribe** — the mic recording is sent to Gemini Flash Lite, which returns plain text.
2. **Retrieve** — the question is embedded and searched against the FAQ vector index. The top matches above a similarity floor (0.65) are kept, deduplicated, and limited to four distinct FAQ entries so multi-topic questions get full coverage.
3. **Rescue search** — if nothing matches, the question is translated to English and searched again, which makes pure-Devanagari questions retrievable against an English FAQ store.
4. **Phrase** — the LLM detects the question's language (English or Hindi), checks the conversation history for follow-ups, and writes a short, natural, spoken-style answer in that language. Hindi answers are composed in Devanagari script so the TTS voice reads them cleanly.
5. **Speak** — the answer is synthesized with Rime Coda using the voice that matches the detected language, and played back while the mic pulses.
6. **Show** — every turn is appended to the chat history with its language tag and a retrieval badge, so the user can see exactly what happened.

---

## Tech stack

| Layer | Tool | Role |
| --- | --- | --- |
| Frontend | **Gradio 6** | Kiosk web UI (mic, chat, status, badges) |
| Speech-to-text | **Google Gemini Flash-Lite** | Audio → text transcription |
| Embeddings | **fastembed (BGE)** | Question → vector |
| Vector database | **Qdrant Cloud** | Cosine-similarity FAQ retrieval |
| Answer phrasing | **Google Gemini Flash-Lite** | Language detection + spoken answer generation |
| Text-to-speech | **Rime Coda** | Text → natural voice (hi/en speakers) |
| Language | **Python 3.11** | Everything in between (requests, pydub, python-dotenv) |

> `Gemini 3.1 Flash-Lite` handles both transcription and answer phrasing at high speed. `Gemma 4 26B` is used only in the offline authoring scripts (`generate_faqs.py`, `expand_faq.py`) that build the FAQ knowledge base.

---

## Project structure

```
.
├── app.py               # Kiosk UI + full voice loop (Gradio)
├── pipeline.py          # Core Q&A logic: retrieval, language detection, phrasing
├── setup_qdrant.py      # One-time: embed FAQ variants and index them in Qdrant
├── generate_faqs.py     # Optional: generate FAQ topics with an LLM
├── expand_faq.py        # Optional: expand each FAQ into natural phrasing variants
├── faq_data.json        # Base knowledge base (70 Q&As)
├── faq_expanded.json    # Expanded variants (70 FAQs, 288 phrases) — indexed
├── test_search.py       # Smoke test for vector search
├── test_rime.py         # Smoke test for Rime TTS
└── requirements.txt
```

---

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/TrigunMishra/VoiceofCampus.git
cd VoiceofCampus
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Add your API keys

```bash
cp .env.example .env
```

Fill in the four keys:

| Variable | Service | Where to get it |
| --- | --- | --- |
| `GEMINI_API_KEY` | Google AI Studio (transcription + LLM) | https://aistudio.google.com |
| `QDRANT_URL`, `QDRANT_API_KEY` | Qdrant Cloud (vector DB) | https://cloud.qdrant.io |
| `RIME_API_KEY` | Rime (text-to-speech) | https://app.rime.ai |

All three offer free tiers.

### 3. Index the FAQ knowledge base (one time)

```bash
.venv/bin/python setup_qdrant.py
```

This embeds all 288 FAQ variants and creates the `campus_faq` collection.

### 4. Launch the kiosk

```bash
.venv/bin/python app.py
```

Open the printed URL (default `http://127.0.0.1:7860`), press the mic, and ask away.

> No UI needed? Try the pipeline directly: `.venv/bin/python pipeline.py` and type questions.

---

## Try it

| Type | Example | What happens |
| --- | --- | --- |
| English | "What are the mess timings?" | Spoken English answer, green **Matched** badge |
| Hindi | "मेस के समय क्या हैं?" | Spoken Hindi answer (Devanagari, Hindi voice), **HI** tag |
| Hinglish | "library ke timings kya hain?" | Hindi answer, **HI** tag |
| Compound | "Where is the library and what are its timings?" | Both parts answered |
| Follow-up | "What about on weekends?" | Answered from conversation context |
| Unanswerable | "How much does the hostel cat weigh?" | Graceful "I'm not sure" fallback, amber badge |

---

## Configuration

| Setting | How | Effect |
| --- | --- | --- |
| Voices | `RIME_EN_SPEAKER` / `RIME_HI_SPEAKER` in `app.py` | Switch English/Hindi TTS speakers |
| Similarity floor | `SIMILARITY_GRACE_FLOOR` in `pipeline.py` | Lower = more forgiving matches |
| History depth | `MAX_HISTORY_TURNS` in `pipeline.py` | How many prior turns feed follow-ups |
| Personalized greeting | Set `CAMPUS_USER_NAME` env var, or create `user_profile.json` with `{"name": "Ada"}` | Header shows "Welcome back, Ada!" |

---

## Performance

Measured on our setup (typical single turn):

| Step | Time |
| --- | --- |
| Qdrant search | ~0.3 s |
| LLM phrasing (Flash-Lite) | ~1–2 s |
| Rime TTS (~5–10 s of audio) | ~2–3 s |
| **Full spoken turn** | **~3–6 s** |

We originally used a 26B parameter model for answer phrasing; each call took ~20 s. Switching to **Gemini Flash-Lite** cut answer generation by roughly **20x**, bringing the full voice loop down to a few seconds — the difference between a frustrating demo and a natural kiosk experience.

---

## Extending the knowledge base

1. Edit `faq_data.json` (list of `{"question", "answer"}` objects) with your own Q&As.
2. *(Optional)* generate new topics: `.venv/bin/python generate_faqs.py`.
3. *(Optional)* expand questions into natural variants for better retrieval: `.venv/bin/python expand_faq.py`.
4. Re-index: `.venv/bin/python setup_qdrant.py`.

---

## Acknowledgments

- **Rime** — lifelike multilingual TTS voices (Coda model)
- **Qdrant** — fast, developer-friendly vector database
- **Google AI Studio / Gemini** — speech-to-text and generation
- **Gradio** — the beautiful, component-rich web framework behind the kiosk UI
