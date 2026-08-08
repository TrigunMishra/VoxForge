import os

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "campus_faq"

if not QDRANT_URL or not QDRANT_API_KEY:
    raise SystemExit("Set QDRANT_URL and QDRANT_API_KEY in your .env file first.")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

embedding_model = TextEmbedding()

question = input("Ask a question: ").strip()
if not question:
    raise SystemExit("No question entered.")

query_vector = list(embedding_model.embed([question]))[0]

result = client.query_points(
    collection_name=COLLECTION_NAME,
    query=query_vector,
    limit=1,
)

if not result.points:
    print("No matching result found.")
else:
    best = result.points[0]
    print(f"Best match (score: {best.score:.4f})")
    print(f"Question: {best.payload['question']}")
    print(f"Answer: {best.payload['answer']}")
