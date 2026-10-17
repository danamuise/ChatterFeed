import json
import os
import sys

from openai import OpenAI


MODEL = os.getenv("CHATTERFEED_AI_MODEL", "gpt-6-luna")

SYSTEM_PROMPT = """
You are the ChatterFeed language interpreter.

Evaluate ONLY the language contained in the supplied social-media post.
Do not infer the author's identity, demographics, ideology, mental state,
intentions beyond what the text supports, or anything from the platform/source.

Return exactly one JSON object and no markdown.

Scoring rubric:

valence: -1.0 to +1.0
  -1.0 = extremely negative emotional tone
   0.0 = emotionally neutral
  +1.0 = extremely positive emotional tone

All other dimensions use 0.0 to 1.0:
  0.0 = absent
  0.25 = weak
  0.50 = moderate
  0.75 = strong
  1.0 = extreme

Dimensions:
- intensity: emotional force or charge
- aggression: hostility, contempt, anger, attack
- warmth: kindness, affection, friendliness, empathy
- certainty: absolute/confident language
- humor: joking, playful, comedic tone
- sarcasm: ironic or mocking inversion
- sadness: grief, despair, melancholy
- conspiratorial: hidden plots, secret actors, coordinated deception
- dehumanizing: treating people/groups as lesser, vermin, objects, etc.
- violent_rhetoric: threats, calls for harm, glorification of violence
- sexual_explicitness: explicit sexual language or description
- confidence: confidence in this interpretation based only on the text

Important:
- Score the text itself, not whether a claim is true or false.
- Quoted, reclaimed, satirical, or condemnatory language should be interpreted
  in context rather than triggered by keywords alone.
- A post may score high on several dimensions simultaneously.
- Keep rationale to one short sentence describing the linguistic evidence.

Required JSON keys:
{
  "valence": number,
  "intensity": number,
  "aggression": number,
  "warmth": number,
  "certainty": number,
  "humor": number,
  "sarcasm": number,
  "sadness": number,
  "conspiratorial": number,
  "dehumanizing": number,
  "violent_rhetoric": number,
  "sexual_explicitness": number,
  "confidence": number,
  "rationale": string
}
""".strip()

NUMERIC_KEYS = [
    "valence",
    "intensity",
    "aggression",
    "warmth",
    "certainty",
    "humor",
    "sarcasm",
    "sadness",
    "conspiratorial",
    "dehumanizing",
    "violent_rhetoric",
    "sexual_explicitness",
    "confidence",
]


def extract_json(text: str) -> dict:
    """Parse a JSON object, tolerating accidental surrounding text."""
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("AI response did not contain a JSON object.")
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("AI response was not a JSON object.")

    return data


def validate_scores(data: dict) -> dict:
    """Validate and normalize the interpreter response."""
    missing = [key for key in NUMERIC_KEYS if key not in data]
    if missing:
        raise ValueError("Missing score fields: " + ", ".join(missing))

    result = {}

    for key in NUMERIC_KEYS:
        value = float(data[key])

        if key == "valence":
            value = max(-1.0, min(1.0, value))
        else:
            value = max(0.0, min(1.0, value))

        result[key] = round(value, 3)

    result["rationale"] = str(data.get("rationale", "")).strip()
    return result


def evaluate_post(client: OpenAI, post: str) -> dict:
    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=post,
    )

    return validate_scores(extract_json(response.output_text))


def print_result(result: dict) -> None:
    print("\n--- ChatterFeed AI interpretation ---")
    for key in NUMERIC_KEYS:
        print(f"{key:22} {result[key]:>6.3f}")
    print(f"{'rationale':22} {result['rationale']}")
    print("-------------------------------------\n")


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.")
        print()
        print("Windows Command Prompt:")
        print('  set OPENAI_API_KEY=your-key-here')
        print()
        print("PowerShell:")
        print('  $env:OPENAI_API_KEY="your-key-here"')
        print()
        print("Then run this program again.")
        sys.exit(1)

    client = OpenAI()

    print("ChatterFeed AI Interpreter")
    print(f"Model: {MODEL}")
    print("Paste one social-media post and press Enter.")
    print("Type q and press Enter to quit.\n")

    while True:
        try:
            post = input("Post> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return

        if post.lower() in {"q", "quit", "exit"}:
            print("Stopped.")
            return

        if not post:
            continue

        try:
            result = evaluate_post(client, post)
            print_result(result)
        except Exception as error:
            print(f"Interpreter error: {error}\n")


if __name__ == "__main__":
    main()
