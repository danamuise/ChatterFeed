import re
from collections.abc import Iterable


class MessageSanitizer:
    """Create a display-safe copy of a post without modifying the raw text."""

    PROFANITY = {
        "asshole",
        "bitch",
        "bullshit",
        "cunt",
        "dick",
        "fuck",
        "fucked",
        "fucker",
        "fucking",
        "motherfucker",
        "pussy",
        "shit",
    }

    SLURS = {
        "chink",
        "fag",
        "faggot",
        "kike",
        "nigger",
        "retard",
        "spic",
        "tranny",
    }

    @staticmethod
    def _mask_terms(
        text: str,
        terms: Iterable[str],
        mask_character: str,
    ) -> str:
        for term in sorted(set(terms), key=len, reverse=True):
            pattern = re.compile(
                rf"(?<!\w){re.escape(term)}(?!\w)",
                re.IGNORECASE,
            )
            text = pattern.sub(
                lambda match: mask_character * len(match.group(0)),
                text,
            )
        return text

    def clean(
        self,
        text: str,
        redaction_spans: list[tuple[int, int]] | None = None,
    ) -> str:
        """
        Return a sanitized display copy.

        redaction_spans is reserved for contextual AI redactions. Spans refer
        to character offsets in the original raw text and are applied before
        deterministic word masking.
        """
        safe_text = text

        if redaction_spans:
            characters = list(safe_text)
            for start, end in redaction_spans:
                start = max(0, start)
                end = min(len(characters), end)
                if start < end:
                    characters[start:end] = ["█"] * (end - start)
            safe_text = "".join(characters)

        safe_text = self._mask_terms(safe_text, self.SLURS, "█")
        safe_text = self._mask_terms(safe_text, self.PROFANITY, "*")
        return safe_text
