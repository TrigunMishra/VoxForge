import os
import tempfile

import gradio as gr
import requests
from dotenv import load_dotenv
from google import genai

from pipeline import answer_question

load_dotenv()

GEMINI_MODEL = "gemini-3.6-flash"
RIME_URL = "https://users.rime.ai/v1/rime-tts"
RIME_HEADERS = {
    "Authorization": f"Bearer {os.getenv('RIME_API_KEY')}",
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def transcribe(audio_path: str) -> str:
    audio_file = gemini.files.upload(file=audio_path)
    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            "Transcribe the speech in this audio to plain text. "
            "Only output the transcription, nothing else.",
            audio_file,
        ],
    )
    return response.text.strip()


def synthesize(text: str) -> str:
    payload = {
        "text": text,
        "speaker": "celeste",
        "modelId": "coda",
        "language": "en",
    }
    response = requests.post(RIME_URL, headers=RIME_HEADERS, json=payload)
    response.raise_for_status()
    out_path = os.path.join(tempfile.mkdtemp(), "reply.mp3")
    with open(out_path, "wb") as f:
        f.write(response.content)
    return out_path


def handle_question(audio_path: str):
    if not audio_path:
        return "", "", None, "No audio received"
    try:
        question = transcribe(audio_path)
        answer = answer_question(question)
        reply_audio = synthesize(answer)
        return question, answer, reply_audio, "Done"
    except Exception as exc:
        return "", "", None, f"Error: {exc}"


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
    demo.launch()
