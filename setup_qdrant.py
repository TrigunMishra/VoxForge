import json
import os

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "campus_faq"
SOURCE_FILE = "faq_expanded.json"

if not QDRANT_URL or not QDRANT_API_KEY:
    raise SystemExit("Set QDRANT_URL and QDRANT_API_KEY in your .env file first.")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)

embedding_model = TextEmbedding()

if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(COLLECTION_NAME)
    print(f"Deleted existing collection '{COLLECTION_NAME}'")

dimension = len(next(embedding_model.embed(["dimension probe"])))
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
)
print(f"Created collection '{COLLECTION_NAME}' (dimension {dimension})")

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    faqs = json.load(f)

points = []
point_id = 0
for faq in faqs:
    variants = faq.get("variants", [faq["question"]])
    for embedding in embedding_model.embed(variants):
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "question": faq["question"],
                    "answer": faq["answer"],
                },
            )
        )
        point_id += 1

client.upsert(collection_name=COLLECTION_NAME, points=points)
print(f"Indexed {len(points)} FAQ variants into '{COLLECTION_NAME}'")
