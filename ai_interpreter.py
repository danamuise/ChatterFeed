import json
import os
import sys

from openai import OpenAI


MODEL = os.getenv("CHATTERFEED_AI_MODEL", "gpt-5.6-luna")

SYSTEM_PROMPT = """
You are the ChatterFeed language interpreter.

Evaluate ONLY the language contained in the supplied social-media post.
Do not infer the author's identity, demographics, ideology, mental state,
intentions beyond what the text supports, or anything from the platform/source.

Return exactly one JSON object and no markdown.

Scoring rubric:

valence: -1.0 to +1.0
  This is SOCIAL / INTERPERSONAL TONE, NOT conventional sentiment or happiness.
  ChatterFeed uses valence to choose a physical marker color.
  -1.0 = extreme hostility, deliberate cruelty, dehumanization, threats,
         advocacy of harm, or vicious personal attacks
   0.0 = factual, detached, or socially neutral language
  +1.0 = exceptional compassion, kindness, human connection, encouragement,
         or expressions of care and solidarity

  Crucial distinction: sadness is NOT negative valence. Grief, loneliness,
  shame, embarrassment, regret, fear, vulnerability, and honest disclosures
  of painful experiences are HUMAN expressions, not hostility. When expressed
  without aggression or cruelty, they MUST receive valence ABOVE ZERO,
  usually +0.10 to +0.40, even if sadness and intensity are very high.
  Strong empathy or compassionate support can score substantially higher.
  Sadness and negative valence may coexist ONLY when the language itself
  also contains hostility or cruelty; do not penalize sadness in that case.
  Do not treat the mere discussion of mental health, illness, trauma,
  discrimination, or loss as negative behavior.

  Disagreement, criticism of an idea, profanity expressing frustration,
  or descriptions of bad events are NOT inherently hostile to people.
  The author's own cruelty or contempt is what drives negative scores,
  not the unpleasantness of what they describe. A quote condemning hateful
  speech is not an endorsement of it.

  Calibration examples (illustrative, not rigid rules):
  - "I felt ashamed after a hospital stay and lost someone I loved."
    valence about +0.25, sadness high, intensity moderate, aggression 0.
  - "I'm having such a hard day. I feel alone."
    valence about +0.20, sadness high, aggression 0.
  - "I'm sorry you're hurting; I am here for you."
    valence about +0.85, warmth high, aggression 0.
  - "I disagree with this policy because it causes delays."
    valence about 0.00, aggression low.
  - "The train arrived at noon."
    valence 0.00, intensity low.
  - "You are worthless and deserve to suffer."
    valence about -0.90, aggression high.
  Score the actual interpersonal stance in context, never the topic alone.

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
- Score sadness independently of valence. High sadness must NOT by itself
  reduce valence, and vulnerability without hostility has positive valence.
- When a post describes personal suffering without attacking anyone, the
  rationale should explicitly note its non-hostile or vulnerable nature.
- Keep rationale to one short sentence describing the linguistic evidence.
- In rationale, do not repeat quoted post text, profanity, slurs, or private
  identifying details. Describe the linguistic features generically so the
  rationale is appropriate for public display.

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


def read_multiline_post() -> str | None:
    """Read a post exactly as pasted, including blank lines."""
    print("Paste the post below.")
    print("When finished, type /end on a new line and press Enter.")
    print("Type q on the first line to quit.\n")

    lines: list[str] = []
    first_line = True

    while True:
        prompt = "Post> " if first_line else "...   "

        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

        command = line.strip().lower()

        if first_line and command in {"q", "quit", "exit"}:
            return None

        if command == "/end":
            return "\n".join(lines).strip()

        lines.append(line)
        first_line = False


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
    print("Multiline posts are preserved exactly for interpretation.\n")

    while True:
        post = read_multiline_post()

        if post is None:
            print("\nStopped.")
            return

        if not post:
            print("No post entered.\n")
            continue

        try:
            result = evaluate_post(client, post)
            print_result(result)
        except Exception as error:
            print(f"Interpreter error: {error}\n")


if __name__ == "__main__":
    main()
