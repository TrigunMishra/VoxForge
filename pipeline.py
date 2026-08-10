import json
import os
import re
import time

from dotenv import load_dotenv
from fastembed import TextEmbedding
from google import genai
from qdrant_client import QdrantClient

load_dotenv()

COLLECTION_NAME = "campus_faq"
SIMILARITY_GRACE_FLOOR = 0.65
FALLBACK_ANSWER = "I'm not sure about that one — ask a senior or check the orientation desk."

_qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=120,
)
_qdrant.get_collections()
_embedding_model = TextEmbedding()
_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

LLM_MODEL = "gemini-3.1-flash-lite"


MAX_HISTORY_TURNS = 3


def _build_conversation_context(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines = "\n".join(
        f"User: {turn['question']}\nAssistant: {turn['answer']}"
        for turn in history
    )
    return f"Earlier in this conversation:\n{lines}\n\n"


def _translate_to_english(text: str) -> str:
    prompt = (
        "The user asked the campus guide a question, possibly in Hindi, "
        "Hinglish, or Devanagari script. Translate it to simple, plain "
        "English. Reply with ONLY the English translation, nothing else."
    )
    response = _gemini.models.generate_content(
        model=LLM_MODEL,
        contents=f"{prompt}\n\n{text}",
        config=genai.types.GenerateContentConfig(
            max_output_tokens=80,
            thinking_config=genai.types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    return response.text.strip()


def _retrieve_candidates(question: str, limit: int = 5) -> list:
    t = time.perf_counter()
    query_vector = list(_embedding_model.embed([question]))[0]
    result = _qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
    )
    print(f"  [timing] qdrant search: {time.perf_counter() - t:.2f}s")
    candidates = [p for p in result.points if p.score >= SIMILARITY_GRACE_FLOOR][:3]
    if candidates:
        print(f"  [info] matched FAQ (score {candidates[0].score:.4f}, {len(candidates)} candidates)")
    return candidates


def _build_faq_block(candidates: list) -> str:
    lines = []
    for i, p in enumerate(candidates, 1):
        lines.append(
            f"FAQ {i}:\nQuestion: {p.payload['question']}\n"
            f"Answer: {p.payload['answer']}"
        )
    return "\n\n".join(lines)


def _parse_lang_answer(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned)
        answer = str(data.get("answer", "")).strip()
        lang = data.get("language", "en")
        if lang not in ("hi", "en"):
            lang = "en"
        if answer:
            return answer, lang
    except (json.JSONDecodeError, AttributeError):
        pass
    return cleaned, "en"


def _answer_from_context(question: str, history: list[dict]) -> tuple[str, str]:
    prompt = (
        "You are a friendly campus guide continuing a conversation. "
        "Use the recent conversation below to answer the user's latest "
        "question. If it refers to something mentioned earlier (e.g. "
        "'what about on weekends?'), answer about that same topic. "
        "Detect whether the user's latest question is in Hindi/Hinglish "
        "or English, and reply with a natural, spoken-sounding answer of "
        "ONE short sentence, under 20 words, entirely in that same "
        "language. When answering in Hindi, write the answer in Devanagari "
        "script (देवनागरी), never Romanized Hinglish. "
        "Use no markdown, bullets, or asterisks. Output ONLY "
        'strict JSON like {"language": "hi", "answer": "..."}.\n\n'
        f"{_build_conversation_context(history)}"
        f"User: {question}"
    )
    response = _gemini.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=300,
            thinking_config=genai.types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    return _parse_lang_answer(response.text)


def answer_question(question: str, history: list[dict] | None = None) -> tuple[str, str]:
    candidates = _retrieve_candidates(question)

    if not candidates:
        print("  [info] no FAQ match, translating query to English and retrying")
        translated = _translate_to_english(question)
        if translated and translated.lower() != question.lower():
            candidates = _retrieve_candidates(translated)

    if not candidates:
        if history:
            print("  [info] still no FAQ match, using conversation memory")
            return _answer_from_context(question, history)
        return FALLBACK_ANSWER, "en"

    prompt = (
        "You are a friendly campus guide. "
        + _build_conversation_context(history)
        + "The user asked a question, and a few possibly-relevant FAQ "
        "entries are listed below. First detect whether the user's question "
        "is in Hindi/Hinglish or English. Then reply with a natural, "
        "spoken-sounding answer of ONE or TWO short sentences, entirely in "
        "that same language, using ONLY the FAQ entries that actually "
        "answer the question. If the question has multiple parts (e.g. "
        "'where is the library and what are its timings?'), answer each "
        "part using the relevant FAQ entries. When answering in Hindi, "
        "write the answer in Devanagari script (देवनागरी), never Romanized "
        "Hinglish. If the user is asking a follow-up that refers to the "
        "earlier conversation (e.g. 'what about on weekends?'), answer "
        "about that same topic using the context above. If none of the FAQ "
        "entries actually answer the question, reply with exactly: "
        "'I'm not sure about that one — ask a senior or check the "
        "orientation desk.' Do not mention FAQ entries, scores, or that you "
        "used a knowledge base. Use no markdown, bullets, or asterisks. "
        "Sound like you are talking to a student. "
        'Output ONLY strict JSON like {"language": "hi", "answer": "..."} '
        'or {"language": "en", "answer": "..."}.\n\n'
        f"User question: {question}\n\n"
        f"{_build_faq_block(candidates)}"
    )

    t = time.perf_counter()
    response = _gemini.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=400,
            thinking_config=genai.types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    print(f"  [timing] llm generation: {time.perf_counter() - t:.2f}s")
    return _parse_lang_answer(response.text)


if __name__ == "__main__":
    print("Type questions to test the pipeline (or 'q' to quit).")
    while True:
        question = input("\n> ").strip()
        if question.lower() in ("q", "quit"):
            break
        if not question:
            continue
        answer, lang = answer_question(question)
        print(f"[{lang}] {answer}")
