import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

VARIANTS_PER_QUESTION = 3
BATCH_SIZE = 3
OUTPUT_FILE = "faq_expanded.json"

gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def expand_batch(questions: list[str]) -> list[dict]:
    numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = (
        "For each numbered question below, write "
        f"{VARIANTS_PER_QUESTION} different natural ways a student might "
        "ASK the exact same thing. Keep every variant a short, natural "
        "spoken question. Output ONLY strict JSON: a list of objects with "
        '"question" (the original) and "variants" (a list of strings). '
        "No markdown, no code fences.\n\n"
        f"{numbered}"
    )
    response = gemini.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=1500,
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
    with open("faq_data.json", "r", encoding="utf-8") as f:
        faqs = json.load(f)

    expanded = []
    for start in range(0, len(faqs), BATCH_SIZE):
        batch = faqs[start : start + BATCH_SIZE]
        print(f"  expanding batch {start // BATCH_SIZE + 1}...")
        try:
            results = expand_batch([q["question"] for q in batch])
        except Exception as exc:
            print(f"  ERROR on batch: {exc}")
            continue
        for faq, res in zip(batch, results):
            variants = res.get("variants", [])
            variants = [v for v in variants if v.strip()]
            variants.insert(0, faq["question"])
            expanded.append({"question": faq["question"], "variants": variants, "answer": faq["answer"]})
        time.sleep(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(expanded, f, indent=2, ensure_ascii=False)

    total = sum(len(e["variants"]) for e in expanded)
    print(f"Wrote {len(expanded)} FAQs with {total} total variants -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
