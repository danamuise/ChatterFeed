import re


class MessageSanitizer:
    """
    Creates a public-safe display version of a message.

    Important: sanitization happens AFTER classification so the classifier
    always receives the original message text.
    """

    def __init__(self) -> None:
        # Keep this list separate from classification logic.
        # "example_slur" is only a placeholder for development.
        self.slurs = {"example_slur"}

        self.obscenities = {
            "fuck",
            "fucking",
            "shit",
            "damn",
        }

    @staticmethod
    def _replace_words(text: str, words: set[str], replacement_factory) -> str:
        for word in sorted(words, key=len, reverse=True):
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            text = pattern.sub(lambda match: replacement_factory(match.group(0)), text)
        return text

    def clean(self, text: str) -> str:
        # Slurs are fully redacted with solid blocks.
        text = self._replace_words(
            text,
            self.slurs,
            lambda word: "█" * max(5, len(word)),
        )

        # Obscenities are replaced with asterisks.
        text = self._replace_words(
            text,
            self.obscenities,
            lambda word: "*" * len(word),
        )

        return text
