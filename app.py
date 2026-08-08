import os
import re
import tempfile
import time

import gradio as gr
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydub import AudioSegment

from pipeline import answer_question

load_dotenv()

GEMINI_MODEL = "gemini-3.1-flash-lite"
RIME_URL = "https://users.rime.ai/v1/rime-tts"
RIME_HEADERS = {
    "Authorization": f"Bearer {os.getenv('RIME_API_KEY')}",
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
RIME_SAMPLE_RATE = 44100

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
rime_session = requests.Session()
rime_session.get(RIME_URL)


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


def synthesize(text: str) -> str:
    cleaned = clean_text_for_tts(text)
    payload = {
        "text": cleaned,
        "speaker": "celeste",
        "modelId": "coda",
        "language": "en",
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


def handle_question(audio_path: str):
    if not audio_path:
        yield "", "", None, "No audio received"
        return
    t_total = time.perf_counter()
    try:
        question = transcribe(audio_path)
        yield question, "", None, "Transcribed — finding the answer..."
        answer = answer_question(question)
        yield question, answer, None, "Answer ready — generating speech..."
        reply_audio = synthesize(answer)
        elapsed = time.perf_counter() - t_total
        print(f"  [timing] total: {elapsed:.2f}s")
        yield question, answer, reply_audio, f"Done ({elapsed:.2f}s)"
    except Exception as exc:
        yield "", "", None, f"Error: {exc}"


with gr.Blocks(title="Campus Voice Assistant") as demo:
    gr.Markdown("# Campus Voice Assistant")
    gr.Markdown("Press the mic, record a question, and hear the answer.")

    mic = gr.Audio(
        label="Ask a question",
        sources=["microphone"],
        type="filepath",
        waveform_options=gr.WaveformOptions(
            waveform_color="#00c2a8",
            waveform_progress_color="#00a08a",
        ),
    )
    output_audio = gr.Audio(label="Spoken answer", type="filepath", autoplay=True)
    question_text = gr.Textbox(label="Transcribed question", interactive=False)
    answer_text = gr.Textbox(label="Answer text", interactive=False)
    status = gr.Label(label="Status")

    mic.change(
        handle_question,
        inputs=mic,
        outputs=[question_text, answer_text, output_audio, status],
    )


if __name__ == "__main__":
    demo.queue().launch()
