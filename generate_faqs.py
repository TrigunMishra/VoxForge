import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

OUTPUT_FILE = "faq_data.json"

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_faqs(topic: str) -> list[dict]:
    prompt = (
        "You are writing the FAQ knowledge base for a university campus "
        "guide. Generate 5-7 question/answer entries about the topic below "
        "using realistic boilerplate campus information (typical timings, "
        "locations, and policies; mark anything that usually varies by "
        "institution as approximate). Keep every answer accurate-sounding, "
        "natural, and written in complete sentences. Use short bullet "
        "lists where helpful.\n\n"
        f"Topic: {topic}\n\n"
        "Output ONLY strict JSON: a list of objects with a \"question\" "
        "(one natural question a student might ask) and an \"answer\" "
        "(the response). No markdown, no code fences."
    )
    response = gemini.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=2500,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def main():
    topics = [
        "mess / dining hall: menu, meal timings (breakfast, lunch, snacks, dinner), "
        "weekend and holiday schedule, meal passes or coupons, guest meals, and contact",
        "hostels: allotment, types of rooms, timings, rules, wardens, wifi, and facilities",
        "campus transport and commuting: college buses, routes, timings, parking, and cabs",
        "fees and payments: tuition fee payment process, fee deadlines, refunds, and scholarships",
        "health services: campus medical centre, first aid, ambulance, and health insurance",
        "wifi and internet: campus wifi availability, login, and IT helpdesk contact",
        "sports facilities: gym, playgrounds, courts, timings, and how to book",
        "student services: identity card, transcript requests, bonafide certificates, and helpdesk",
    ]
    new_faqs = []
    for topic in topics:
        print(f"  generating FAQs for: {topic.split(':')[0]}...")
        try:
            faqs = generate_faqs(topic)
            for f in faqs:
                if f.get("question") and f.get("answer"):
                    new_faqs.append({"question": f["question"], "answer": f["answer"]})
        except Exception as exc:
            print(f"  ERROR on topic: {exc}")

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    questions = {e["question"].strip().lower() for e in existing}
    added = 0
    for entry in new_faqs:
        if entry["question"].strip().lower() not in questions:
            existing.append(entry)
            questions.add(entry["question"].strip().lower())
            added += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

    print(f"Added {added} new FAQs. Total now: {len(existing)}")


if __name__ == "__main__":
    main()
