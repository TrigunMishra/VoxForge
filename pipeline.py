import os
import re
import time

from dotenv import load_dotenv
from fastembed import TextEmbedding
from google import genai
from qdrant_client import QdrantClient

load_dotenv()

COLLECTION_NAME = "campus_faq"
SIMILARITY_THRESHOLD = 0.75
MAX_DIRECT_ANSWER_WORDS = 20
FALLBACK_ANSWER = "I'm not sure about that one — ask a senior or check the orientation desk."

_qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
_qdrant.get_collections()
_embedding_model = TextEmbedding()
_gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _can_use_directly(answer: str) -> bool:
    if len(answer.split()) > MAX_DIRECT_ANSWER_WORDS:
        return False
    return not re.search(r"[*_#`>~\[\]|]|^\s*[-•]", answer, flags=re.MULTILINE)


def answer_question(question: str) -> str:
    t = time.perf_counter()
    query_vector = list(_embedding_model.embed([question]))[0]
    result = _qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=1,
    )
    print(f"  [timing] qdrant search: {time.perf_counter() - t:.2f}s")

    if not result.points or result.points[0].score < SIMILARITY_THRESHOLD:
        return FALLBACK_ANSWER

    best = result.points[0]
    print(f"  [info] matched FAQ (score {best.score:.4f})")

    faq_answer = best.payload["answer"]
    if _can_use_directly(faq_answer):
        print("  [info] FAQ answer short + clean, skipping LLM")
        return faq_answer

    prompt = (
        "You are a friendly campus guide. Given the user's question, "
        "the matched FAQ question, and its answer, reply with a natural, "
        "spoken-sounding answer of ONE short sentence, under 20 words. "
        "Do not include the original FAQ text verbatim and use no markdown, "
        "bullets, or asterisks. Sound like you are talking to a student.\n\n"
        f"User question: {question}\n"
        f"FAQ question: {best.payload['question']}\n"
        f"FAQ answer: {best.payload['answer']}"
    )

    t = time.perf_counter()
    response = _gemini.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=200,
            thinking_config=genai.types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    print(f"  [timing] llm generation: {time.perf_counter() - t:.2f}s")
    return response.text.strip()


if __name__ == "__main__":
    print("Type questions to test the pipeline (or 'q' to quit).")
    while True:
        question = input("\n> ").strip()
        if question.lower() in ("q", "quit"):
            break
        if not question:
            continue
        print(answer_question(question))
