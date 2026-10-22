import os

from openai import OpenAI


MODEL = os.getenv(
    "CHATTERFEED_SANITIZER_MODEL",
    os.getenv("CHATTERFEED_AI_MODEL", "gpt-5.6-luna"),
)

SANITIZER_PROMPT = """
Sanitize this social-media post for public display.
Preserve the text exactly except for words or passages that should be redacted.
Use * for profanity/obscenity and █ for slurs or hateful terms.
Return only the sanitized post.
""".strip()


class MessageSanitizer:
    """Send a post to the AI sanitizer and return its sanitized version."""

    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI()

    def clean(self, text: str) -> str:
        response = self.client.responses.create(
            model=MODEL,
            instructions=SANITIZER_PROMPT,
            input=text,
        )

        sanitized = response.output_text

        if not sanitized:
            raise ValueError("AI sanitizer returned an empty response.")

        return sanitized
