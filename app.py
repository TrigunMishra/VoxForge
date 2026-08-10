import html
import json
import os
import re
import tempfile
import time
import traceback

import gradio as gr
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydub import AudioSegment

from pipeline import (
    MAX_HISTORY_TURNS,
    answer_question,
)

load_dotenv()

GEMINI_MODEL = "gemini-3.1-flash-lite"
RIME_URL = "https://users.rime.ai/v1/rime-tts"
RIME_HEADERS = {
    "Authorization": f"Bearer {os.getenv('RIME_API_KEY')}",
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
RIME_SAMPLE_RATE = 44100
RIME_EN_SPEAKER = "celeste"
RIME_HI_SPEAKER = "nadi"

APP_NAME = "Voice of Campus"
TAGLINE = "Press the mic and ask anything about campus."
IDLE_TEXT = "Tap the mic and ask a question"
PRIMARY = "#0aa8a7"
PRIMARY_DARK = "#0a8f8e"

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
rime_session = requests.Session()
rime_session.get(RIME_URL)


def load_user_name() -> str | None:
    name = os.getenv("CAMPUS_USER_NAME")
    if name:
        return name.strip()
    try:
        with open("user_profile.json") as f:
            return str(json.load(f).get("name", "")).strip() or None
    except (OSError, ValueError):
        return None


USER_NAME = load_user_name()


# ---------------------------------------------------------------- pipeline


def transcribe(audio_path: str) -> str:
    t0 = time.perf_counter()
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    print(f"  [timing] read audio: {time.perf_counter() - t0:.2f}s")

    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            "Transcribe the speech in this audio to plain text. "
            "Only output the transcription, nothing else.",
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
        ],
    )
    t1 = time.perf_counter()
    print(f"  [timing] transcription call: {t1 - t0:.2f}s")
    return response.text.strip()


def clean_text_for_tts(text: str) -> str:
    cleaned = re.sub(r"[*_#`>~\[\]|]", "", text)
    cleaned = re.sub(r"^\s*[-•]\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def synthesize(text: str, language: str = "en") -> str:
    cleaned = clean_text_for_tts(text)
    speaker = RIME_HI_SPEAKER if language == "hi" else RIME_EN_SPEAKER
    payload = {
        "text": cleaned,
        "speaker": speaker,
        "modelId": "coda",
        "language": language,
        "samplingRate": RIME_SAMPLE_RATE,
    }
    t0 = time.perf_counter()
    response = rime_session.post(RIME_URL, headers=RIME_HEADERS, json=payload)
    response.raise_for_status()
    t1 = time.perf_counter()
    print(f"  [timing] rime tts call: {t1 - t0:.2f}s")

    out_path = os.path.join(tempfile.mkdtemp(), "reply.mp3")
    with open(out_path, "wb") as f:
        f.write(response.content)

    audio = AudioSegment.from_mp3(out_path)
    print(
        f"  [info] rime audio: frame_rate={audio.frame_rate}Hz "
        f"channels={audio.channels} (requested {RIME_SAMPLE_RATE}Hz)"
    )
    return out_path


# ---------------------------------------------------------------- chat model


def _user_message(question: str, lang: str) -> dict:
    tag = "HI" if lang == "hi" else "EN"
    text = f"{html.escape(question)} <span class='lang-tag'>{tag}</span>"
    return {"role": "user", "content": [{"type": "text", "text": text}]}


def _badge_html(meta: dict | None) -> str:
    meta = meta or {}
    if meta.get("matched_faq") and not meta.get("fallback"):
        pct = int(round((meta.get("score") or 0) * 100))
        faq = html.escape(meta["matched_faq"])
        return (
            f"<span class='badge badge-match'>"
            f"Matched · {faq} · {pct}% similarity</span>"
        )
    return (
        "<span class='badge badge-nomatch'>"
        "No strong match — fallback used</span>"
    )


def _assistant_message(answer: str, lang: str, meta: dict | None) -> dict:
    tag = "HI" if lang == "hi" else "EN"
    text = (
        f"{html.escape(answer)} <span class='lang-tag'>{tag}</span>\n\n"
        f"{_badge_html(meta)}"
    )
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


# ---------------------------------------------------------------- kiosk UI


def _status_html(state: str, text: str) -> str:
    return (
        f"<div class='status st-{state}'>"
        f"<span class='orb'></span>"
        f"<span class='status-text'>{html.escape(text)}</span>"
        f"</div>"
    )


def _mic_update(state: str | None):
    classes = ["kiosk-mic"]
    if state in ("listening", "speaking"):
        classes.append("active")
    return gr.update(elem_classes=classes)


def _header_html() -> str:
    subtitle = f"Welcome back, {html.escape(USER_NAME)}!" if USER_NAME else TAGLINE
    return (
        f"<div class='kiosk-header'>"
        f"<div class='app-logo'></div>"
        f"<h1>{APP_NAME}</h1>"
        f"<p class='tagline'>{html.escape(subtitle)}</p>"
        f"</div>"
    )


CSS = """
.gradio-container {
    max-width: 880px !important;
    margin: 0 auto !important;
    padding-top: 1.6rem !important;
    padding-bottom: 3rem !important;
}

/* Header */
.kiosk-header { text-align: center; padding: 0.6rem 0 1.2rem; }
.kiosk-header .app-logo {
    width: 64px; height: 64px; margin: 0 auto 0.8rem;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #3cc8c7, #0a8f8e);
    box-shadow: 0 10px 24px rgba(10, 168, 167, 0.35);
}
.kiosk-header h1 {
    font-size: 2.9rem; font-weight: 800; margin: 0;
    letter-spacing: -0.5px; color: #0b5f5f;
}
.kiosk-header .tagline {
    font-size: 1.3rem; font-weight: 500;
    margin: 0.5rem 0 0; color: #557a79;
}

/* Status indicator */
#kiosk-status { text-align: center; margin: 0.4rem 0 0.4rem; }
#kiosk-status .status {
    display: inline-flex; align-items: center; gap: 0.6rem;
    font-size: 1.25rem; font-weight: 600; color: #2f5a59;
}
#kiosk-status .orb {
    width: 16px; height: 16px; border-radius: 50%;
    background: #c7d6d5; display: inline-block;
}
#kiosk-status .st-listening .orb,
#kiosk-status .st-speaking .orb {
    background: #0aa8a7;
    animation: orb-pulse 1.2s ease-in-out infinite;
}
#kiosk-status .st-thinking .orb {
    background: #f59e0b;
    animation: orb-blink 1s steps(2, start) infinite;
}
@keyframes orb-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(10, 168, 167, 0.5); }
    50%      { box-shadow: 0 0 0 12px rgba(10, 168, 167, 0); }
}
@keyframes orb-blink { 50% { opacity: 0.35; } }

/* Big centered mic */
.mic-col { align-items: center; justify-content: center; }
.kiosk-mic { width: min(400px, 92vw) !important; }
.kiosk-mic .audio-container {
    height: 190px !important; align-items: center;
}
.kiosk-mic .record-button {
    height: 92px !important; width: 92px !important;
    border-radius: 50% !important; border: 3px solid #0aa8a7 !important;
    background: #fff !important; justify-content: center !important;
    padding: 0 !important; margin: 0 auto !important;
}
.kiosk-mic .record-button:before {
    height: 34px !important; width: 34px !important;
    background: #0aa8a7 !important; margin: 0 !important;
    border-radius: 50% !important;
}
.kiosk-mic.active .record-button { animation: mic-pulse 1.4s ease-out infinite; }
@keyframes mic-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(10, 168, 167, 0.45); }
    100% { box-shadow: 0 0 0 28px rgba(10, 168, 167, 0); }
}

/* Chat history */
#kiosk-chat { --chatbot-text-size: 1.05rem; margin-top: 0.8rem; }
#kiosk-chat .message.bot .bubble {
    background: #f3faf9; border: 1px solid #dceeee;
}
#kiosk-chat .message.user .bubble {
    background: #e7f5f4; border: 1px solid #d0e9e8;
}
#kiosk-chat .message-row { padding: 0.3rem 0; }

/* Spoken-answer player */
.kiosk-player { max-width: 400px !important; margin: 0 auto 0.4rem !important; }

/* Language tag + match badge */
.lang-tag {
    display: inline-block; font-size: 0.72em; font-weight: 800;
    padding: 2px 10px; border-radius: 999px; margin-left: 6px;
    background: #e3f4f7; color: #0a6a7a;
    border: 1px solid #bfe3e9; vertical-align: middle;
}
.badge {
    display: inline-block; font-size: 0.82em; font-weight: 700;
    padding: 4px 12px; border-radius: 999px; margin-top: 4px;
}
.badge-match {
    background: #e7f6ef; color: #14724a; border: 1px solid #b9e6cf;
}
.badge-nomatch {
    background: #fdf0dd; color: #92600a; border: 1px solid #efd9a6;
}
"""


def handle_question(audio_path: str, conv: list, chat: list):
    chat = list(chat or [])
    conv = list(conv or [])

    if not audio_path:
        yield (
            gr.update(value=None),
            _status_html("idle", IDLE_TEXT),
            chat,
            chat,
            conv,
            gr.update(),
        )
        return

    t_total = time.perf_counter()
    try:
        question = transcribe(audio_path)
        if not question:
            gr.Warning("Didn't catch that, try again")
            yield (
                gr.update(value=None),
                _status_html("idle", IDLE_TEXT),
                chat,
                chat,
                conv,
                gr.update(),
            )
            return

        yield (
            gr.update(value=None),
            _status_html("thinking", "Thinking…"),
            chat,
            chat,
            conv,
            gr.update(),
        )

        answer, language, meta = answer_question(question, conv)
        conv = (conv + [{"question": question, "answer": answer}])[-MAX_HISTORY_TURNS:]
        chat = chat + [
            _user_message(question, language),
            _assistant_message(answer, language, meta),
        ]

        yield (
            gr.update(value=None),
            _status_html("thinking", "Thinking…"),
            chat,
            chat,
            conv,
            gr.update(),
        )

        reply_audio = synthesize(answer, language)
        elapsed = time.perf_counter() - t_total
        print(f"  [timing] total: {elapsed:.2f}s")

        yield (
            gr.update(value=None),
            _status_html("speaking", "Speaking…"),
            chat,
            chat,
            conv,
            gr.update(value=reply_audio),
        )
    except Exception:
        print(traceback.format_exc())
        gr.Warning("Didn't catch that, try again")
        yield (
            gr.update(value=None),
            _status_html("idle", IDLE_TEXT),
            chat,
            chat,
            conv,
            gr.update(),
        )


def on_recording_start():
    return _mic_update("listening"), _status_html("listening", "Listening…")


def on_playback_end():
    return _mic_update("idle"), _status_html("idle", IDLE_TEXT)


theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.teal,
    secondary_hue=gr.themes.colors.sky,
    neutral_hue=gr.themes.colors.slate,
    radius_size=gr.themes.sizes.radius_lg,
    text_size=gr.themes.sizes.text_lg,
)

with gr.Blocks(title=APP_NAME) as demo:
    gr.HTML(_header_html(), elem_id="kiosk-header")

    status = gr.HTML(_status_html("idle", IDLE_TEXT), elem_id="kiosk-status")

    with gr.Column(elem_classes=["mic-col"]):
        mic = gr.Audio(
            sources=["microphone"],
            type="filepath",
            elem_classes=["kiosk-mic"],
            waveform_options=gr.WaveformOptions(
                waveform_color=PRIMARY,
                waveform_progress_color=PRIMARY_DARK,
            ),
        )

    output_audio = gr.Audio(
        label="Spoken answer",
        type="filepath",
        autoplay=True,
        elem_classes=["kiosk-player"],
    )

    chatbot = gr.Chatbot(
        elem_id="kiosk-chat",
        elem_classes=["chat-wrap"],
        height=440,
        autoscroll=True,
        sanitize_html=False,
        placeholder="Ask a question by pressing the mic above.",
    )

    conv = gr.State([])
    chat = gr.State([])

    mic.start_recording(
        on_recording_start,
        outputs=[mic, status],
        trigger_mode="always_last",
    )

    mic.stop_recording(
        handle_question,
        inputs=[mic, conv, chat],
        outputs=[mic, status, chatbot, chat, conv, output_audio],
        trigger_mode="always_last",
    )

    output_audio.stop(on_playback_end, outputs=[mic, status])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(theme=theme, css=CSS)
