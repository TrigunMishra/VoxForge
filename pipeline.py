import os

from dotenv import load_dotenv
from fastembed import TextEmbedding
from google import genai
from qdrant_client import QdrantClient

load_dotenv()

COLLECTION_NAME = "campus_faq"
SIMILARITY_THRESHOLD = 0.75
FALLBACK_ANSWER = "I'm not sure about that one — ask a senior or check the orientation desk."


def answer_question(question: str) -> str:
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    embedding_model = TextEmbedding()

    query_vector = list(embedding_model.embed([question]))[0]
    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=1,
    )

    if not result.points or result.points[0].score < SIMILARITY_THRESHOLD:
        return FALLBACK_ANSWER

    best = result.points[0]
    print(f"[matched {best.score:.4f}]")

    prompt = (
        "You are a friendly campus guide. Given the user's question, "
        "the matched FAQ question, and its answer, phrase a natural, "
        "spoken-sounding answer of one or two sentences. Do not include "
        "the original FAQ text verbatim; sound like you are talking to "
        f"a student.\n\nUser question: {question}\n"
        f"FAQ question: {best.payload['question']}\n"
        f"FAQ answer: {best.payload['answer']}"
    )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return FALLBACK_ANSWER

    gemini = genai.Client(api_key=api_key)
    response = gemini.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
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
