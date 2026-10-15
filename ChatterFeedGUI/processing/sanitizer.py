import re


class MessageSanitizer:
    """Creates a public-safe display version of a message."""

    def __init__(self) -> None:
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
        text = self._replace_words(
            text,
            self.slurs,
            lambda word: "█" * max(5, len(word)),
        )
        text = self._replace_words(
            text,
            self.obscenities,
            lambda word: "*" * len(word),
        )
        return text
