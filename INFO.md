# Campus Voice Assistant — Complete Project Guide

A plain-English walkthrough of everything we built, written for someone
with **no programming background** who must present this project to a
judging committee and answer tough questions.

If you read this document top to bottom once, you will understand:
*what* the project does, *why* we chose each piece of technology, *how*
the pieces connect, *how fast* it is, and *how to answer questions* a
committee is likely to ask.

---

## Table of Contents

1. [Elevator pitch (30 seconds)](#1-elevator-pitch-30-seconds)
2. [The problem we are solving](#2-the-problem-we-are-solving)
3. [What the user experiences](#3-what-the-user-experiences)
4. [The big picture — a 5-stage pipeline](#4-the-big-picture--a-5-stage-pipeline)
5. [Every piece of the project, explained](#5-every-piece-of-the-project-explained)
6. [The technology choices and why we made them](#6-the-technology-choices-and-why-we-made-them)
7. [Performance — how fast it is and how we made it faster](#7-performance--how-fast-it-is-and-how-we-made-it-faster)
8. [Security and privacy](#8-security-and-privacy)
9. [Cost — the whole project is free to run](#9-cost--the-whole-project-is-free-to-run)
10. [How to run the project yourself](#10-how-to-run-the-project-yourself)
11. [Live demo script (what to say to judges)](#11-live-demo-script-what-to-say-to-judges)
12. [Anticipated judge questions and good answers](#12-anticipated-judge-questions-and-good-answers)
13. [Jargon-to-English dictionary](#13-jargon-to-english-dictionary)
14. [Limitations we are honest about](#14-limitations-we-are-honest-about)
15. [What we would build next](#15-what-we-would-build-next)

---

## 1. Elevator pitch (30 seconds)

> "We built a **voice-powered campus guide**. A visitor walks up to a
> screen, presses a button, and asks in their own words — 'Where do I get
> a student ID?' — and the system answers out loud in a natural, friendly
> voice in about three and a half seconds.
>
> Under the hood it works like a librarian with three helpers: a
> **memory** that stores the campus FAQ as meaning, not text; a **brain**
> that turns a stored answer into something that sounds human; and a
> **voice** that reads it out loud. It also knows when it *doesn't* know
> something, and politely says so instead of guessing.
>
> Every part uses free services, and we measured the whole thing end to
> end to prove it is fast enough to feel like a real conversation."

---

## 2. The problem we are solving

Every new student, parent, or visitor asks the **same handful of
questions**: where is the library, when does it open, where do I get an
ID, which building hosts which department. At a campus like JSS Noida,
these questions are repeated hundreds of times a day.

The usual ways to answer them all have weaknesses:

| Existing option | Weakness |
| --- | --- |
| A person at an information desk | Expensive, not available 24/7, repetitive |
| A website / PDF FAQ | You have to search, read, and scroll — slow and unfriendly |
| A chatbot that matches exact keywords | Fails when you phrase things differently |

Our system fixes all three problems at once:

- **Always available** — a computer never sleeps.
- **No reading required** — it *speaks* the answer.
- **Understands meaning, not exact words** — you can ask "where's the
  library?" or "how do I borrow books?" and it still understands, because
  it matches on *meaning*, not on exact spelling.

And crucially, it is **honest**: when it isn't confident it has the right
answer, it tells the user to ask a human, instead of making something up.

---

## 3. What the user experiences

```
 ┌────────────────────────────────────────────┐
 │        Campus Voice Assistant              │
 │                                            │
 │   [ 🎤  Press the mic and ask a question ] │
 │                                            │
 │   Transcribed question:  Where do I get a  │
 │                          student ID?       │
 │   Answer text:  Student ID cards are issued│
 │                 at the records office...   │
 │                                            │
 │   [ ▶  Spoken answer plays automatically ] │
 │                                            │
 │   Status:  Done (3.65s)                    │
 └────────────────────────────────────────────┘
```

The user presses a microphone button, speaks, and within a few seconds:

1. The **transcription** of their words appears on screen almost
   immediately.
2. The **written answer** appears.
3. A **spoken answer** plays out loud automatically.

Showing the text on screen alongside the audio is a deliberate design
choice — if the audio ever sounds wrong, you can see exactly what the
system *thought* you said and what it *decided* to answer. This makes
debugging easy and makes the system feel trustworthy.

---

## 4. The big picture — a 5-stage pipeline

Think of the system as a **factory assembly line**. Raw material (your
voice) goes in one end, and a finished product (a spoken answer) comes out
the other. Each station does one small job:

```
  STAGE 1           STAGE 2           STAGE 3             STAGE 4             STAGE 5
 ┌─────────┐      ┌─────────┐      ┌───────────┐       ┌───────────┐       ┌─────────┐
 │ HEARING │ ──►  │ HEARING │ ──►  │  MEMORY   │  ──►  │   BRAIN   │  ──►  │  VOICE  │
 │ Micro-  │      │ (Google │      │ Qdrant    │       │ (Google   │       │ Rime    │
 │ phone   │      │ Gemini  │      │ vector DB │       │ Gemma 4)  │       │ Coda TTS│
 │ records │      │ 3.1     │      │ +         │       │ rephrases │       │ speaks  │
 │ your    │      │ Flash   │      │ fastembed │       │ the answer│       │ the     │
 │ voice   │      │ Lite)   │      │ search    │       │ naturally │       │ answer  │
 └─────────┘      └─────────┘      └───────────┘       └───────────┘       └─────────┘
    1.6s             1.6s            0.4s                1.8s                1.6s
```

Wait — a few notes to avoid confusion when you present this:

- **Stage 1 and Stage 2** together are "turning your voice into words"
  (speech-to-text). We lump "recording" and "transcribing" together.
- **Stage 3** (memory) has a **gate**: a similarity score. If the score is
  too low, the system says *"I'm not sure about that one — ask a senior or
  check the orientation desk."* and **skips Stages 4 and 5 entirely** —
  which is why uncertain questions are answered in under a second.
- **Stage 4** is sometimes **skipped even when we have a match**: if the
  stored answer is already short and clean, there's no need to have the
  brain rewrite it. We measured that this saves about 1.8 seconds.

The key insight to communicate to judges: **the system is modular**. Each
stage is a separate, testable piece. You can upgrade the voice without
touching the memory, or swap the brain without touching anything else.

---

## 5. Every piece of the project, explained

### The project folder

```
rime-tts/
├── app.py             ← the web app (the screen the user sees)
├── pipeline.py        ← the brain + memory logic (the thinking)
├── setup_qdrant.py    ← fills the memory with FAQs (run once)
├── test_search.py     ← a test tool to check the memory
├── test_rime.py       ← a test tool for the voice (run once)
├── faq_data.json      ← the FAQ knowledge base (the facts)
├── requirements.txt   ← the shopping list of software packages
├── .env               ← secret API keys (NEVER shared or uploaded)
├── .env.example       ← a blank template showing which keys are needed
├── .gitignore         ← tells Git which files must NOT be uploaded
└── README.md          ← this document
```

### `faq_data.json` — the facts

A plain text file containing the campus questions and answers, for
example:

```json
{
  "question": "Where is the library?",
  "answer": "The library is open from 9:00 AM to 8:00 PM on weekdays..."
}
```

This is the project's **memory of facts**. Right now it has six sample
questions we wrote for testing. In a real deployment, this file would be
replaced with the college's full FAQ list — no code changes needed, just
more data.

### `setup_qdrant.py` — preparing the memory (run once)

Computers do not understand words. They only understand **numbers**. So
before the system can answer anything, we have to convert every FAQ
question into numbers. That is what this script does:

1. Connects to **Qdrant Cloud** — an online database built specially for
   storing "meaning numbers".
2. Uses **fastembed** to turn every question into a list of **384
   numbers** (this list is called an *embedding*). Sentences with similar
   meaning produce similar numbers.
3. Stores each question's numbers in the database, along with the original
   question and answer attached as the *payload* (the extra information
   carried along).

**Analogy:** imagine writing every FAQ on an index card, and instead of
filing them alphabetically, you file each card in the spot that matches
its *meaning*. Questions about the library sit near each other, even if
the words are different ("Where is the library?" and "How do I borrow
books?" are filed close together).

### `test_search.py` — checking the memory

A small tool for us (the developers). You type a question, and it:
1. Converts your question to numbers, the same way the setup script does.
2. Asks Qdrant: *"which stored card has the closest meaning?"*
3. Prints the best match and a **similarity score** from 0 to 1
   (1.0 = identical meaning, 0 = completely unrelated).

This is how we verified the memory works before building the rest.

### `pipeline.py` — the thinking

The heart of the project. It exposes one function:

```python
answer_question(question) -> answer
```

What happens inside:

1. **Search** — your question is converted to numbers and Qdrant finds the
   closest stored FAQ.
2. **Gate (the confidence check)** — if the similarity score is above
   **0.75**, the system is confident. If it's below, it returns a polite
   "I'm not sure" message and stops.
3. **Shortcut** — if the stored answer is already short (under 20 words)
   and free of formatting symbols, use it directly. No brain needed.
4. **Brain (Gemma 4)** — otherwise, send the matched Q&A plus the user's
   original question to Google's **Gemma 4** model, which rewrites the
   answer to sound natural and spoken — like a real person talking to you,
   not like a document being read aloud.
5. **Return** — the final answer text.

The similarity threshold of 0.75 is a **design decision we can tune**.
Raise it and the system gets more cautious; lower it and it answers more
often but risks being wrong.

### `test_rime.py` — the voice, tested (run once)

Sends a sentence to **Rime's Coda** text-to-speech service, which turns
text into spoken audio, and saves it as `test_output.mp3`. The comment in
the code marks exactly where you would change the voice or language later
(e.g. from English to Hindi, or from one speaker voice to another).

### `app.py` — the web app (what the user actually sees)

Built with a Python framework called **Gradio**. This is the file that
ties everything together into a real user interface:

- A **microphone button** (records your voice).
- A **transcription box** (shows what you said).
- An **answer text box** (shows the written answer).
- An **audio player** (plays the spoken answer automatically).
- A **status line** (shows how long it took).

When you record a question, it runs the full pipeline in order:
1. Transcribe the audio (Google Gemini 3.1 Flash Lite).
2. Answer the question (the pipeline above).
3. Turn the answer into speech (Rime Coda).
4. Play it back and display the text.

Because we made the app "stream" its progress, you see the transcription
appear instantly, then the answer text, then hear the audio — instead of
waiting frozen for several seconds. This makes it feel responsive.

### Supporting files

| File | Purpose | Analogy |
| --- | --- | --- |
| `requirements.txt` | The list of software packages to install | A grocery list |
| `.env` | Stores secret API keys | The safe where passwords live |
| `.env.example` | Blank template of which keys are needed | A checklist |
| `.gitignore` | Tells Git not to upload secrets/caches | A "do not pack this" list |

---

## 6. The technology choices and why we made them

This is where committees probe. Here is the "why" behind each choice, and
honest alternatives we considered.

### Speech-to-text (your voice → words)

- **Chosen:** Google **Gemini 3.1 Flash Lite** (a model designed for
  exactly this job).
- **Why:** It is fast (about 1.6 seconds), accurate, free on Google's
  free tier, and works through the same API we already use.
- **Alternatives:** OpenAI's Whisper (paid API or heavy to run locally);
  other paid STT services. We picked Google because we could use the free
  tier and one consistent API.

### The memory (searching the FAQ)

- **Chosen:** **Qdrant Cloud** (a *vector database*) + **fastembed** to
  make the "meaning numbers".
- **Why:** Traditional databases search for exact text matches. We need
  *meaning* matches — "how do I borrow books" must find the library card.
  Vector databases are the standard modern tool for this (it is the "R" in
  RAG — Retrieval-Augmented Generation).
- **Why fastembed specifically:** free, runs locally, uses a compact model
  (384 numbers per sentence), fast enough for real time.
- **Alternatives:** Pinecone, Weaviate, Chroma (other vector databases);
  running Qdrant on our own server instead of the cloud.

### The brain (turning facts into natural speech)

- **Chosen:** Google **Gemma 4 26B** (an open-source, free model).
- **Why:** It is free, runs well on Google's free tier, and is excellent
  at natural language. We deliberately **turned off its "thinking" mode**
  because thinking slows it down and is unnecessary for a simple rewrite
  task — this cut that stage from ~4.8 seconds to ~1.8 seconds.
- **Alternatives:** Gemini 3.6 Flash (we hit its free-tier rate limit, so
  we switched), Claude, GPT (both paid — we kept the project free).

### The voice (text → speech)

- **Chosen:** **Rime Coda**.
- **Why:** Specifically designed for natural, *conversational* speech (it
  is marketed for phone agents and voice assistants), which is exactly our
  use case.
- **Important detail:** We discovered Rime's default output is 24,000 Hz
  audio, which sounds a bit muffled. We explicitly request **44,100 Hz**
  (CD-quality) and verify the returned file matches. This was one of the
  fixes for the "robotic" sound.

### The user interface

- **Chosen:** **Gradio**.
- **Why:** Built for exactly this — creating a web UI for AI apps in
  minutes, with built-in microphone recording and audio playback. No
  front-end web development needed.

### The glue language

- **Python** — the most widely used language for AI projects, so all the
  AI libraries (Gemini, Qdrant, fastembed, Rime) have clean Python
  support.

---

## 7. Performance — how fast it is and how we made it faster

Judges love hard numbers. Here is our honest measurement story.

**A real test question:** "Where can I get a student ID printed?"

### Before optimization (first working version): **14–16 seconds**

We knew that was too slow to feel like a real conversation.

### First round of fixes: **~10 seconds**

1. **Timing instrumentation** — we added stopwatch prints around every
   stage so we could *see* where time went instead of guessing.
2. **Sample-rate fix** — 24 kHz → 44.1 kHz (also fixed the muffled sound).
3. **Removed markdown symbols** before sending text to the voice, so it
   didn't read out asterisks and bullets.
4. **Moved setup out of the hot path** — the database connection and the
   embedding model were being re-created on *every single question*.
   We now create them once, at startup.
5. **Shortened the brain's output** — a prompt that forces a one-sentence
   answer, so both the AI and the voice have less to produce.

### Final round of fixes: **~3.6 seconds** (4× faster)

| Optimization | How it works | Time saved |
| --- | --- | --- |
| Send audio inline | Stop uploading the audio file as a separate step; send it directly in the same request | ~3.2s |
| Skip the brain when unnecessary | If the stored answer is already short and clean, use it as-is | ~1.8s |
| Reuse the network connection | Keep one open connection to Rime instead of opening a new one each time | ~0.6s |
| Warm up the database | Ping Qdrant once at startup so the connection is ready | ~0.9s |
| Stream the UI | Show transcription immediately instead of all at once at the end | feels instant |

### The measured timing breakdown (final)

```
[timing] read audio:          0.00s
[timing] transcription call:  1.61s   (voice → words)
[timing] qdrant search:       0.40s   (memory lookup)
[info] FAQ answer short + clean, skipping LLM
[timing] rime tts call:       1.56s   (words → voice)
[timing] total:               3.65s
```

**When the system is uncertain**, it answers the fallback message in about
**0.3 seconds** because it skips the brain and the voice entirely.

If a judge asks "is it fast enough?" — yes: 3.65 seconds is within the
range of normal human turn-taking in conversation.

---

## 8. Security and privacy

- **API keys never live in code.** They are stored in `.env`, a local file
  that is listed in `.gitignore` so it can never be accidentally uploaded
  to a public repository. `.env.example` shows only the *names* of the
  keys needed, never the values.
- **Free-tier access only.** We used free tiers throughout, so there is no
  billing risk or exposure of payment data.
- **No personal data collected.** The system does not ask for, store, or
  transmit any personal information. Audio is used for the single
  transcription call and not retained by our code.
- **Fail-safe behaviour.** If an API key is missing or a service fails, the
  app shows an error message rather than crashing or exposing internals.
- **Honest failure.** When confidence is low, the system recommends asking
  a human — it does not fabricate answers.

---

## 9. Cost — the whole project is free to run

| Service | What it does | Cost |
| --- | --- | --- |
| Google AI Studio (Gemini 3.1 Flash Lite + Gemma 4) | Transcription + brain | Free tier |
| Qdrant Cloud | Vector memory | Free tier (small collection) |
| Rime Coda | Voice | Free credits (a few cents per 1,000 characters normally) |
| Gradio / Python / fastembed | UI + glue + embeddings | Free, open source |

This is a strong point for a committee: a working, end-to-end voice AI
project that costs nothing to build and almost nothing to run.

---

## 10. How to run the project yourself

```bash
# 1. Create a virtual environment and install the packages (once)
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Create the .env file and paste your API keys in it
#    (QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY, RIME_API_KEY)
cp .env.example .env

# 3. Fill the database with FAQs (once)
.venv/bin/python setup_qdrant.py

# 4. (Optional) test the voice
.venv/bin/python test_rime.py

# 5. Test the brain from the command line
.venv/bin/python pipeline.py

# 6. Launch the web app — open the printed URL in your browser
.venv/bin/python app.py
```

A live demo in front of judges only needs step 6 (the database is already
filled). Make sure `.env` has real keys before the demo.

---

## 11. Live demo script (what to say to judges)

> **Opening (30s):** "Good morning. We built a voice assistant for campus.
> I'll show you — it takes a spoken question and answers it out loud in a
> few seconds."
>
> **Press the mic, ask:** "Where can I get a student ID printed?"
>
> **While it works, narrate:** "It just transcribed my voice. Now it's
> searching its memory of the campus FAQ by meaning, not by exact words —
> so I could have said 'ID card' or 'student pass' and it would still find
> the right answer. Then it speaks the answer."
>
> **When audio plays:** "That's the answer spoken in a natural voice.
> You'll notice the text is on screen too, so if anything sounded wrong we
> could see what it understood."
>
> **Now show the honesty feature — ask:** "What's the meaning of life on
> campus?"
>
> **When it says it's not sure:** "It doesn't know this one, and instead of
> guessing it tells you to ask a human. That's deliberate — it only answers
> when it's confident, above a similarity score of 0.75."
>
> **Close:** "Everything you saw — the hearing, the memory, the brain, and
> the voice — uses free services, and the whole thing responds in about
> three and a half seconds."

---

## 12. Anticipated judge questions and good answers

### "How does it actually find the right answer?"
The questions in our FAQ were converted into lists of numbers (embeddings)
that capture their meaning. When a user asks something, we convert their
question into the same kind of numbers and ask the database to return the
stored question whose numbers are closest. Similar meaning → similar
numbers → closest match. This is why rephrasing still works.

### "What is a vector database and why not a normal database?"
A normal database compares text letter-by-letter, so "how do I borrow
books" and "where is the library" look unrelated. A vector database
compares *meaning*, so those two phrases land next to each other. For a
voice assistant, meaning matching is essential.

### "What does the similarity score mean?"
It's a number from 0 to 1 measuring how confident the system is that the
stored card answers the question. 1.0 = essentially the same question;
0 = unrelated. We answer only above 0.75. It's a tunable knob — higher =
safer but more "I don't know" replies.

### "Why do you use three different AI services?"
Because each is best at one job: one converts voice to words (hearing),
one rewrites text to sound natural (thinking), and one converts words to
voice (speaking). Using the best tool for each job is a deliberate,
modular architecture — and all three happen to be free.

### "Why Gemma 4 instead of GPT or Claude?"
GPT and Claude are excellent but paid. Gemma 4 is Google's free,
open-source model and is more than capable of our one-sentence rewrite
task. We originally used Gemini 3.6 Flash but hit its free-tier rate
limit during testing, so we switched to Gemma 4 — which also let us turn
off its "thinking" mode for extra speed.

### "Why did the audio sound robotic before, and how did you fix it?"
Two causes. First, Rime's default output was 24 kHz, which sounds muffled;
we now request 44.1 kHz CD-quality audio and verify it. Second, the brain
occasionally added markdown symbols (asterisks, bullets) that the voice
read out literally; we now strip those before sending text to the voice.

### "How do you measure 3.65 seconds? Is that reproducible?"
We added stopwatch logs around every stage and printed a total for each
question. It's measured on the actual cloud services, so network speed
varies slightly, but the breakdown (which stages cost what) is stable and
reproducible in the terminal output.

### "What happens if a user asks something the FAQ doesn't cover?"
The similarity score falls below 0.75, and the system returns a fixed,
polite fallback: *"I'm not sure about that one — ask a senior or check the
orientation desk."* It never fabricates an answer.

### "Is this just wrapping existing services? What did YOU build?"
Fair challenge. We built: (1) the end-to-end integration architecture,
(2) the confidence-gated decision logic, (3) the optimization work that
took it from 14 seconds to 3.6 seconds, (4) the modular design that lets
each stage be swapped, and (5) the measurement methodology that proves the
performance. The value is in how the pieces are combined, tuned, and
tested — not in any single library.

### "How would you scale this to the whole campus?"
The FAQ file would hold the full official FAQ (no code change needed). For
heavy traffic you'd enable Qdrant's larger free tier or scale the cloud
instance, and add caching for repeated questions.

---

## 13. Jargon-to-English dictionary

| Term | Plain meaning |
| --- | --- |
| API / API key | A web service's front door; the key is the password that opens it |
| Vector database (Qdrant) | A database that stores "meaning numbers" and finds similar meanings fast |
| Embedding (fastembed) | A sentence converted into numbers that capture its meaning |
| Similarity score | 0–1 number saying how closely a question matches a stored one |
| Threshold (0.75) | The confidence line: above it we answer, below it we say "I'm not sure" |
| Speech-to-text (STT) | Turning spoken words into written text |
| Text-to-speech (TTS) | Turning written text into spoken audio |
| LLM (Gemma 4) | A large language model — an AI that reads and writes text naturally |
| RAG | Retrieval-Augmented Generation — search a knowledge base first, then let an AI phrase the answer |
| Pipeline | A chain of stages, each passing its result to the next |
| Prompt | The instructions you give to an AI model |
| Sample rate (Hz) | How detailed the audio is; 44.1 kHz is CD quality |
| Virtual environment (venv) | An isolated folder for a project's packages so they don't clash |
| Gradio | A Python tool that builds a web UI for AI apps |
| Latency | The time between a question and its answer |

---

## 14. Limitations we are honest about

- **Scope of knowledge:** It only knows what is in the FAQ file. It is a
  campus guide, not a general assistant.
- **Free-tier limits:** Google's free tier allows a limited number of
  requests per minute; a real campus deployment would move to paid tiers.
- **English only right now:** The code supports changing the language, but
  we only tested English.
- **Sample data:** The six FAQs are placeholders we wrote; the real value
  comes with the full official FAQ.
- **Single-turn:** Each question is answered independently. It does not yet
  remember the previous question (no multi-turn conversation).

---

## 15. What we would build next

- **Multi-turn conversation** so follow-up questions ("what about
  weekends?") work naturally.
- **Hindi support** (the code already has a language field ready).
- **Load the real college FAQ** into `faq_data.json`.
- **Cache repeated questions** to answer instantly.
- **A kiosk mode** with a big button and always-on listening.
- **Logging dashboard** to see which questions are asked most, so the
  FAQ can be improved based on real data.
